<?php
// FC-7 Payroll Processing (core). Uses FC-4/5/6, MW-6 transaction manager, MW-7 audit.
class Payroll {
  static function periods() { return Db::all("SELECT * FROM period ORDER BY start_date DESC"); }
  static function createPeriod(array $b, array $u) {
    $s = $b['start_date'] ?? ''; $e = $b['end_date'] ?? '';
    $errs = ['start_date'=>Validate::date($s,'Start date'), 'end_date'=>Validate::date($e,'End date')];
    Validate::collect($errs);
    if ($e < $s) Http::fail('End date cannot be before start date.', 422, ['end_date'=>'Before start date.']);
    if (Db::one("SELECT 1 FROM period WHERE NOT (end_date < ? OR start_date > ?)", [$s,$e])) Http::fail('This period overlaps an existing payroll period.', 409);
    $id = Db::run("INSERT INTO period(start_date,end_date) VALUES(?,?)", [$s,$e]);
    AuditPub::publish($u,'CREATE_PERIOD',"period:$id $s..$e"); return ['id'=>(int)$id];
  }
  static function calculate(int $pid, array $u) {
    $per = Db::one("SELECT * FROM period WHERE id=?", [$pid]);
    if (!$per) Http::fail('Payroll period not found.', 404);
    if ($per['status'] === 'Finalized') Http::fail('Period is finalized and locked.', 409);
    $pdo = Db::pdo(); $pdo->beginTransaction(); // MW-6
    try {
      Db::run("DELETE FROM payroll_result WHERE period_id=?", [$pid]);
      $n = 0;
      foreach (Db::all("SELECT id FROM employee WHERE active=1 AND hire_date <= ?", [$per['end_date']]) as $e) {
        $c = Compensation::get($e['id']);
        if (!$c) continue;
        $h = Attendance::totals($e['id'], $per['start_date'], $per['end_date']);
        if ($c['pay_type'] === 'hourly') { $hr = $c['rate']; $reg = $h['r'] * $hr; }
        else { $hr = $c['rate'] / 2080; $reg = $c['rate'] / 26; }
        $ot = $h['o'] * $hr * $c['ot_multiplier'];
        $gross = round($reg + $ot + $c['bonus'], 2);
        $ded = []; $dt = 0;
        foreach (Deduction::list($e['id']) as $d) { $a = round($d['mode'] === 'percent' ? $gross * $d['value'] / 100 : $d['value'], 2); $ded[] = ['name'=>$d['name'],'amount'=>$a]; $dt += $a; }
        $warn = null; $net = round($gross - $dt, 2);
        if ($dt > $gross) { $warn = 'Deductions exceed gross pay.'; $net = 0; }
        $detail = json_encode(['regular_pay'=>round($reg,2),'overtime_pay'=>round($ot,2),'bonus'=>(float)$c['bonus'],'deductions'=>$ded]);
        Db::run("INSERT INTO payroll_result(period_id,employee_id,regular_hours,overtime_hours,gross,deductions,net,warning,detail) VALUES(?,?,?,?,?,?,?,?,?)",
          [$pid,$e['id'],$h['r'],$h['o'],$gross,round($dt,2),$net,$warn,$detail]); $n++;
      }
      Db::run("UPDATE period SET status='Calculated', calculated_by=? WHERE id=?", [$u['id'],$pid]);
      AuditPub::publish($u,'CALCULATE_PAYROLL',"period:$pid employees:$n");
      $pdo->commit();
    } catch (Throwable $t) { $pdo->rollBack(); Http::fail('Calculation failed; no changes were saved.', 500); }
    return self::results($pid);
  }
  static function results(int $pid) { return Db::all("SELECT r.*, e.first_name||' '||e.last_name name FROM payroll_result r JOIN employee e ON e.id=r.employee_id WHERE period_id=? ORDER BY e.last_name", [$pid]); }
  static function finalize(int $pid, array $u) {
    $per = Db::one("SELECT * FROM period WHERE id=?", [$pid]);
    if (!$per) Http::fail('Payroll period not found.', 404);
    if ($per['status'] === 'Finalized') Http::fail('Period is already finalized.', 409);
    if ($per['status'] !== 'Calculated') Http::fail('Calculate payroll before finalizing.', 409);
    if ((int)$per['calculated_by'] === (int)$u['id']) Http::fail('A second authorized person must finalize this period.', 403);
    Db::run("UPDATE period SET status='Finalized', finalized_by=?, finalized_at=? WHERE id=?", [$u['id'], date('Y-m-d H:i:s'), $pid]);
    AuditPub::publish($u,'FINALIZE_PAYROLL',"period:$pid");
  }
}

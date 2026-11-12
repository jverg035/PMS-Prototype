<?php
// FC-8 Pay Statement (MW-3 record-level rule: employee sees only own data) + FC-9 reporting (one report)
class PayStatement {
  static function periods(array $u) {
    if (!$u['employee_id']) Http::fail('No employee record is linked to this account.', 403);
    return Db::all("SELECT p.id,p.start_date,p.end_date FROM period p JOIN payroll_result r ON r.period_id=p.id WHERE p.status='Finalized' AND r.employee_id=? ORDER BY p.start_date DESC", [$u['employee_id']]);
  }
  static function get(int $pid, array $u, ?int $empId = null) {
    $emp = $u['role'] === 'Employee' ? $u['employee_id'] : $empId;   // record-level rule
    $r = Db::one("SELECT r.*, p.start_date, p.end_date, e.first_name||' '||e.last_name name FROM payroll_result r JOIN period p ON p.id=r.period_id JOIN employee e ON e.id=r.employee_id WHERE r.period_id=? AND r.employee_id=? AND p.status='Finalized'", [$pid, $emp]);
    if (!$r) Http::fail('Pay statement not available.', 404);
    $d = json_decode($r['detail'], true);
    return ['employee'=>$r['name'],'period'=>$r['start_date'].' to '.$r['end_date'],'regular_hours'=>$r['regular_hours'],'overtime_hours'=>$r['overtime_hours'],
      'regular_pay'=>$d['regular_pay'],'overtime_pay'=>$d['overtime_pay'],'bonus'=>$d['bonus'],'gross'=>$r['gross'],'deductions'=>$d['deductions'],'total_deductions'=>$r['deductions'],'net'=>$r['net']];
  }
  static function summaryReport(int $pid) {  // FC-9 Payroll Summary
    $rows = Db::all("SELECT e.first_name||' '||e.last_name name, d.name department, r.gross, r.deductions, r.net FROM payroll_result r JOIN employee e ON e.id=r.employee_id JOIN department d ON d.id=e.department_id WHERE r.period_id=? ORDER BY e.last_name", [$pid]);
    $t = Db::one("SELECT COALESCE(SUM(gross),0) gross, COALESCE(SUM(deductions),0) deductions, COALESCE(SUM(net),0) net FROM payroll_result WHERE period_id=?", [$pid]);
    return ['rows'=>$rows,'totals'=>$t];
  }
}

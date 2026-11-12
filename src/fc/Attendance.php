<?php
// FC-4 Attendance & Time Management
class Attendance {
  const OT_APPROVAL = 10; // overtime above this per day is flagged
  static function save(array $b, array $u) {
    $emp = Db::one("SELECT id FROM employee WHERE id=? AND active=1", [$b['employee_id'] ?? 0]);
    $e = ['employee_id'=>$emp ? null : 'Select an active employee.', 'work_date'=>Validate::date($b['work_date'] ?? '', 'Work date', true),
      'regular'=>Validate::num($b['regular'] ?? '', 'Regular hours', 0, 24), 'overtime'=>Validate::num($b['overtime'] ?? '0', 'Overtime hours', 0, 24)];
    Validate::collect($e);
    if ((float)$b['regular'] + (float)($b['overtime'] ?? 0) > 24) Http::fail('Total hours for one day cannot exceed 24.', 422, ['regular'=>'Total exceeds 24.']);
    $locked = Db::one("SELECT 1 FROM period WHERE status='Finalized' AND ? BETWEEN start_date AND end_date", [$b['work_date']]);
    if ($locked) Http::fail('This date belongs to a finalized payroll period and cannot be changed.', 409);
    Db::run("INSERT INTO attendance(employee_id,work_date,regular,overtime) VALUES(?,?,?,?) ON CONFLICT(employee_id,work_date) DO UPDATE SET regular=excluded.regular, overtime=excluded.overtime",
      [$b['employee_id'],$b['work_date'],(float)$b['regular'],(float)($b['overtime'] ?? 0)]);
    AuditPub::publish($u,'SAVE_ATTENDANCE',"employee:{$b['employee_id']} {$b['work_date']}");
    return ['flag'=>(float)($b['overtime'] ?? 0) > self::OT_APPROVAL ? 'Overtime exceeds approval threshold and is flagged for review.' : null];
  }
  static function list(int $emp, string $from, string $to) { return Db::all("SELECT * FROM attendance WHERE employee_id=? AND work_date BETWEEN ? AND ? ORDER BY work_date", [$emp,$from,$to]); }
  static function totals(int $emp, string $from, string $to) { return Db::one("SELECT COALESCE(SUM(regular),0) r, COALESCE(SUM(overtime),0) o FROM attendance WHERE employee_id=? AND work_date BETWEEN ? AND ?", [$emp,$from,$to]); }
}

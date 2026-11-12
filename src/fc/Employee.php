<?php
// FC-2 Employee Management + FC-3 Department & Position lookups
class Employee {
  static function lookups() { return ['departments'=>Db::all("SELECT * FROM department ORDER BY name"), 'positions'=>Db::all("SELECT * FROM position ORDER BY name")]; }
  static function search(array $q) {
    $sql = "SELECT e.*, d.name department, p.name position FROM employee e JOIN department d ON d.id=e.department_id JOIN position p ON p.id=e.position_id WHERE 1=1"; $p = [];
    if (!empty($q['q'])) { $sql .= " AND (e.first_name LIKE ? OR e.last_name LIKE ? OR CAST(e.id AS TEXT)=?)"; $t = '%'.$q['q'].'%'; array_push($p,$t,$t,$q['q']); }
    if (!empty($q['department_id'])) { $sql .= " AND e.department_id=?"; $p[] = $q['department_id']; }
    return Db::all($sql." ORDER BY e.last_name", $p);
  }
  static function validate(array $b) {
    $deptOk = Db::one("SELECT 1 FROM department WHERE id=?", [$b['department_id'] ?? 0]);
    $posOk = Db::one("SELECT 1 FROM position WHERE id=?", [$b['position_id'] ?? 0]);
    Validate::collect([
      'first_name'=>Validate::name($b['first_name'] ?? '', 'First name'), 'last_name'=>Validate::name($b['last_name'] ?? '', 'Last name'),
      'email'=>Validate::email($b['email'] ?? ''), 'hire_date'=>Validate::date($b['hire_date'] ?? '', 'Hire date', true),
      'department_id'=>$deptOk ? null : 'Select a department.', 'position_id'=>$posOk ? null : 'Select a position.']);
  }
  static function create(array $b, array $u) {
    self::validate($b);
    if (Db::one("SELECT 1 FROM employee WHERE lower(email)=lower(?)", [trim($b['email'])])) Http::fail('An employee with this email already exists.', 409, ['email'=>'Duplicate email.']);
    $id = Db::run("INSERT INTO employee(first_name,last_name,email,department_id,position_id,hire_date) VALUES(?,?,?,?,?,?)",
      [trim($b['first_name']),trim($b['last_name']),trim($b['email']),$b['department_id'],$b['position_id'],$b['hire_date']]);
    AuditPub::publish($u,'CREATE_EMPLOYEE',"employee:$id"); return ['id'=>(int)$id];
  }
  static function deactivate(int $id, array $u) { Db::run("UPDATE employee SET active=0 WHERE id=?", [$id]); AuditPub::publish($u,'DEACTIVATE_EMPLOYEE',"employee:$id"); }
}

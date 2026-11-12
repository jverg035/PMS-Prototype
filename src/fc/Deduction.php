<?php
// FC-6 Deduction Management
class Deduction {
  static function list(int $emp) { return Db::all("SELECT * FROM deduction WHERE employee_id=? ORDER BY id", [$emp]); }
  static function add(array $b, array $u) {
    $emp = Db::one("SELECT id FROM employee WHERE id=?", [$b['employee_id'] ?? 0]);
    $mode = $b['mode'] ?? '';
    $name = trim((string)($b['name'] ?? ''));
    Validate::collect(['employee_id'=>$emp ? null : 'Select an employee.',
      'name'=>$name === '' ? 'Deduction name is required.' : (mb_strlen($name) > 40 ? 'Deduction name must be 40 characters or fewer.' : null),
      'kind'=>in_array($b['kind'] ?? '', ['tax','insurance','retirement','other'], true) ? null : 'Select a deduction type.',
      'mode'=>in_array($mode, ['flat','percent'], true) ? null : 'Select flat amount or percentage.',
      'value'=>Validate::num($b['value'] ?? '', 'Deduction value', 0, $mode === 'percent' ? 100 : 100000, true)]);
    $id = Db::run("INSERT INTO deduction(employee_id,name,kind,mode,value) VALUES(?,?,?,?,?)", [$b['employee_id'],$name,$b['kind'],$mode,(float)$b['value']]);
    AuditPub::publish($u,'ADD_DEDUCTION',"employee:{$b['employee_id']} $name"); return ['id'=>(int)$id];
  }
  static function remove(int $id, array $u) { Db::run("DELETE FROM deduction WHERE id=?", [$id]); AuditPub::publish($u,'REMOVE_DEDUCTION',"deduction:$id"); }
}

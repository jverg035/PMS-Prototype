<?php
// FC-5 Compensation Management
class Compensation {
  static function get(int $emp) { return Db::one("SELECT * FROM compensation WHERE employee_id=?", [$emp]); }
  static function save(array $b, array $u) {
    $emp = Db::one("SELECT id FROM employee WHERE id=?", [$b['employee_id'] ?? 0]);
    $type = $b['pay_type'] ?? '';
    $max = $type === 'salary' ? 1000000 : 1000;
    Validate::collect(['employee_id'=>$emp ? null : 'Select an employee.', 'pay_type'=>in_array($type,['hourly','salary'],true) ? null : 'Select a compensation type.',
      'rate'=>Validate::num($b['rate'] ?? '', 'Rate', 0, $max, true), 'ot_multiplier'=>Validate::num($b['ot_multiplier'] ?? '', 'Overtime multiplier', 1, 3),
      'bonus'=>Validate::num($b['bonus'] ?? '0', 'Bonus', 0, 100000)]);
    Db::run("INSERT INTO compensation(employee_id,pay_type,rate,ot_multiplier,bonus) VALUES(?,?,?,?,?) ON CONFLICT(employee_id) DO UPDATE SET pay_type=excluded.pay_type, rate=excluded.rate, ot_multiplier=excluded.ot_multiplier, bonus=excluded.bonus",
      [$b['employee_id'],$type,(float)$b['rate'],(float)$b['ot_multiplier'],(float)($b['bonus'] ?? 0)]);
    AuditPub::publish($u,'SAVE_COMPENSATION',"employee:{$b['employee_id']}");
  }
}

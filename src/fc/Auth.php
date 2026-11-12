<?php
// FC-1 Authentication & Access Control (uses MW-2, MW-3, MW-7)
class Auth {
  static function login(array $b) {
    $un = trim((string)($b['username'] ?? '')); $pw = (string)($b['password'] ?? '');
    Validate::collect(['username' => $un === '' ? 'Username is required.' : null, 'password' => $pw === '' ? 'Password is required.' : null]);
    $u = Db::one("SELECT * FROM user WHERE username=?", [$un]);
    if (!$u || !$u['active']) { AuditPub::publish(null, 'LOGIN_FAILED', $un); Http::fail('Invalid username or password.', 401); }
    if ($u['locked']) Http::fail('Account locked after 5 failed attempts. Contact a System Administrator.', 423);
    if (!password_verify($pw, $u['pass_hash'])) {
      $f = $u['failed'] + 1;
      Db::run("UPDATE user SET failed=?, locked=? WHERE id=?", [$f, $f >= 5 ? 1 : 0, $u['id']]);
      AuditPub::publish(['id'=>$u['id'],'username'=>$un], 'LOGIN_FAILED', $un);
      Http::fail($f >= 5 ? 'Account locked after 5 failed attempts. Contact a System Administrator.' : 'Invalid username or password.', $f >= 5 ? 423 : 401);
    }
    Db::run("UPDATE user SET failed=0 WHERE id=?", [$u['id']]);
    $s = ['id'=>(int)$u['id'], 'username'=>$u['username'], 'role'=>$u['role'], 'employee_id'=>$u['employee_id'] ? (int)$u['employee_id'] : null];
    Security::login($s); AuditPub::publish($s, 'LOGIN', $un);
    return $s;
  }
  static function menu(string $role): array { // UI-3 role-based menu
    $m = [
      'Payroll Administrator' => ['employees','attendance','compensation','deductions','payroll','reports','audit'],
      'Finance/Accounting' => ['payroll','reports','deductions'],
      'System Administrator' => ['audit','users'],
      'Employee' => ['paystatement'],
    ];
    return $m[$role] ?? [];
  }
  static function users() { return Db::all("SELECT id,username,role,locked,active FROM user ORDER BY id"); }
  static function unlock(int $id, array $u) { Db::run("UPDATE user SET locked=0, failed=0 WHERE id=?", [$id]); AuditPub::publish($u,'UNLOCK_USER',"user:$id"); }
}

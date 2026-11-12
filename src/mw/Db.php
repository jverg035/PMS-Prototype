<?php
// MW-5 Data Access Layer: all SQL lives behind this class; FCs never open the DB themselves.
class Db {
  private static $pdo;
  static function pdo(): PDO {
    if (!self::$pdo) {
      $path = getenv('PMS_DB') ?: __DIR__ . '/../../data/pms.sqlite';
      $fresh = !file_exists($path);
      self::$pdo = new PDO('sqlite:' . $path);
      self::$pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
      self::$pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
      if ($fresh) { self::schema(); require __DIR__ . '/../seed.php'; seed(self::$pdo); }
    }
    return self::$pdo;
  }
  static function all($sql, $p = []) { $s = self::pdo()->prepare($sql); $s->execute($p); return $s->fetchAll(); }
  static function one($sql, $p = []) { $s = self::pdo()->prepare($sql); $s->execute($p); $r = $s->fetch(); return $r ?: null; }
  static function run($sql, $p = []) { $s = self::pdo()->prepare($sql); $s->execute($p); return self::pdo()->lastInsertId(); }
  static function schema() {
    self::pdo()->exec("
    CREATE TABLE department(id INTEGER PRIMARY KEY, name TEXT UNIQUE);
    CREATE TABLE position(id INTEGER PRIMARY KEY, name TEXT UNIQUE);
    CREATE TABLE employee(id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT, email TEXT, department_id INT, position_id INT, hire_date TEXT, active INT DEFAULT 1);
    CREATE TABLE user(id INTEGER PRIMARY KEY, username TEXT UNIQUE, pass_hash TEXT, role TEXT, employee_id INT, failed INT DEFAULT 0, locked INT DEFAULT 0, active INT DEFAULT 1);
    CREATE TABLE period(id INTEGER PRIMARY KEY, start_date TEXT, end_date TEXT, status TEXT DEFAULT 'Open', calculated_by INT, finalized_by INT, finalized_at TEXT);
    CREATE TABLE attendance(id INTEGER PRIMARY KEY, employee_id INT, work_date TEXT, regular REAL, overtime REAL, UNIQUE(employee_id, work_date));
    CREATE TABLE compensation(id INTEGER PRIMARY KEY, employee_id INT UNIQUE, pay_type TEXT, rate REAL, ot_multiplier REAL, bonus REAL DEFAULT 0);
    CREATE TABLE deduction(id INTEGER PRIMARY KEY, employee_id INT, name TEXT, kind TEXT, mode TEXT, value REAL);
    CREATE TABLE payroll_result(id INTEGER PRIMARY KEY, period_id INT, employee_id INT, regular_hours REAL, overtime_hours REAL, gross REAL, deductions REAL, net REAL, warning TEXT, detail TEXT, UNIQUE(period_id, employee_id));
    CREATE TABLE audit(id INTEGER PRIMARY KEY, ts TEXT, user_id INT, username TEXT, action TEXT, record TEXT);
    ");
  }
}

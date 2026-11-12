<?php
// MW-1 REST API / Service Layer: single entry point, routes through MW-2 (auth), MW-3 (role), then to FCs.
foreach (['mw/Db','mw/Http','mw/Security','mw/Audit','mw/Doc','fc/Auth','fc/Employee','fc/Attendance','fc/Compensation','fc/Deduction','fc/Payroll','fc/PayStatement'] as $f) require __DIR__ . "/../src/$f.php";
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
if (strpos($path, '/api/') !== 0) return false;   // static files
$route = substr($path, 5); $m = $_SERVER['REQUEST_METHOD']; $b = Http::body(); $q = $_GET;
try {
  if ($route === 'login' && $m === 'POST') { $s = Auth::login($b); Http::out(['user'=>$s,'menu'=>Auth::menu($s['role'])]); }
  if ($route === 'logout' && $m === 'POST') { Security::logout(); Http::out(['ok'=>true]); }
  if ($route === 'me') { $u = Security::user(); Http::out($u ? ['user'=>$u,'menu'=>Auth::menu($u['role'])] : ['user'=>null]); }
  $u = Security::require();
  $PA = ['Payroll Administrator']; $PF = ['Payroll Administrator','Finance/Accounting'];
  switch (true) {
    case $route === 'lookups': Http::out(Employee::lookups());
    case $route === 'employees' && $m === 'GET': Authz::need($u,$PA); Http::out(Employee::search($q));
    case $route === 'employees' && $m === 'POST': Authz::need($u,$PA); Http::out(Employee::create($b,$u),201);
    case preg_match('#^employees/(\d+)/deactivate$#',$route,$x): Authz::need($u,$PA); Employee::deactivate((int)$x[1],$u); Http::out(['ok'=>true]);
    case $route === 'attendance' && $m === 'POST': Authz::need($u,$PA); Http::out(Attendance::save($b,$u));
    case $route === 'attendance' && $m === 'GET': Authz::need($u,$PA); Http::out(Attendance::list((int)($q['employee_id']??0), $q['from']??'0000-00-00', $q['to']??'9999-12-31'));
    case $route === 'compensation' && $m === 'GET': Authz::need($u,$PA); Http::out(Compensation::get((int)($q['employee_id']??0)) ?: new stdClass);
    case $route === 'compensation' && $m === 'POST': Authz::need($u,$PA); Compensation::save($b,$u); Http::out(['ok'=>true]);
    case $route === 'deductions' && $m === 'GET': Authz::need($u,$PF); Http::out(Deduction::list((int)($q['employee_id']??0)));
    case $route === 'deductions' && $m === 'POST': Authz::need($u,$PF); Http::out(Deduction::add($b,$u),201);
    case preg_match('#^deductions/(\d+)$#',$route,$x) && $m === 'DELETE': Authz::need($u,$PF); Deduction::remove((int)$x[1],$u); Http::out(['ok'=>true]);
    case $route === 'periods' && $m === 'GET': Authz::need($u,$PF); Http::out(Payroll::periods());
    case $route === 'periods' && $m === 'POST': Authz::need($u,$PA); Http::out(Payroll::createPeriod($b,$u),201);
    case preg_match('#^periods/(\d+)/calculate$#',$route,$x): Authz::need($u,$PF); Http::out(Payroll::calculate((int)$x[1],$u));
    case preg_match('#^periods/(\d+)/results$#',$route,$x): Authz::need($u,$PF); Http::out(Payroll::results((int)$x[1]));
    case preg_match('#^periods/(\d+)/finalize$#',$route,$x): Authz::need($u,$PF); Payroll::finalize((int)$x[1],$u); Http::out(['ok'=>true]);
    case preg_match('#^periods/(\d+)/report$#',$route,$x): Authz::need($u,$PF); Http::out(PayStatement::summaryReport((int)$x[1]));
    case $route === 'paystatements': Http::out(PayStatement::periods($u));
    case preg_match('#^paystatements/(\d+)$#',$route,$x): Http::out(PayStatement::get((int)$x[1],$u,isset($q['employee_id'])?(int)$q['employee_id']:null));
    case preg_match('#^paystatements/(\d+)/download$#',$route,$x):
      $s = PayStatement::get((int)$x[1],$u); header('Content-Type: text/html'); header('Content-Disposition: attachment; filename="paystatement.html"'); echo Doc::statement($s); exit;
    case $route === 'audit': Authz::need($u,['System Administrator','Payroll Administrator']);
      $sql="SELECT * FROM audit WHERE 1=1"; $p=[]; if(!empty($q['user'])){$sql.=" AND username=?";$p[]=$q['user'];} if(!empty($q['action'])){$sql.=" AND action=?";$p[]=$q['action'];}
      Http::out(Db::all($sql." ORDER BY id DESC LIMIT 200",$p));
    case $route === 'users': Authz::need($u,['System Administrator']); Http::out(Auth::users());
    case preg_match('#^users/(\d+)/unlock$#',$route,$x): Authz::need($u,['System Administrator']); Auth::unlock((int)$x[1],$u); Http::out(['ok'=>true]);
    default: Http::fail('Not found.', 404);
  }
} catch (PDOException $e) { Http::fail('A system error occurred. No changes were saved.', 500); }

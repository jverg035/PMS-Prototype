<?php
function seed(PDO $db) {
  foreach (['Human Resources','Finance','Engineering','Sales','Operations'] as $d) $db->prepare("INSERT INTO department(name) VALUES(?)")->execute([$d]);
  foreach (['Analyst','Manager','Engineer','Clerk','Director'] as $p) $db->prepare("INSERT INTO position(name) VALUES(?)")->execute([$p]);
  $emps = [['Maria','Lopez','maria.lopez@pms.test',3,3,'2024-03-04'],['James','Carter','james.carter@pms.test',2,1,'2023-08-14'],['Aisha','Khan','aisha.khan@pms.test',4,4,'2025-01-20'],['Daniel','Okafor','daniel.okafor@pms.test',1,2,'2022-11-02']];
  foreach ($emps as $e) $db->prepare("INSERT INTO employee(first_name,last_name,email,department_id,position_id,hire_date) VALUES(?,?,?,?,?,?)")->execute($e);
  $users = [['padmin','Payroll123!','Payroll Administrator',null],['fin1','Finance123!','Finance/Accounting',null],['sysadmin','SysAdmin123!','System Administrator',null],['maria','Employee123!','Employee',1],['james','Employee123!','Employee',2]];
  foreach ($users as $u) $db->prepare("INSERT INTO user(username,pass_hash,role,employee_id) VALUES(?,?,?,?)")->execute([$u[0], password_hash($u[1], PASSWORD_DEFAULT), $u[2], $u[3]]);
  $comp = [[1,'hourly',40.00,1.5,100],[2,'salary',78000,1.5,0],[3,'hourly',25.50,1.5,0],[4,'salary',95000,1.5,250]];
  foreach ($comp as $c) $db->prepare("INSERT INTO compensation(employee_id,pay_type,rate,ot_multiplier,bonus) VALUES(?,?,?,?,?)")->execute($c);
  $ded = [[1,'Federal Tax','tax','percent',12],[1,'Health Insurance','insurance','flat',85],[2,'Federal Tax','tax','percent',15],[3,'Federal Tax','tax','percent',10],[4,'Retirement','retirement','percent',5]];
  foreach ($ded as $d) $db->prepare("INSERT INTO deduction(employee_id,name,kind,mode,value) VALUES(?,?,?,?,?)")->execute($d);
}

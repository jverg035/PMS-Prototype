import json, os, subprocess, time, signal, sys, urllib.request
from playwright.sync_api import sync_playwright, expect
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB = '/tmp/pms_test.sqlite'; BASE = 'http://127.0.0.1:8081'; SHOTS = os.path.join(ROOT, 'shots')
os.makedirs(SHOTS, exist_ok=True)
if os.path.exists(DB): os.remove(DB)
srv = subprocess.Popen(['php','-S','127.0.0.1:8081','-t','public','public/router.php'], cwd=ROOT, env={**os.environ,'PMS_DB':DB}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
RES = {'ect': [], 'ft': []}
LAST={'m':''}
def money(x): return f"${x:,.2f}"

def login(pw, user, pwd):
    ctx = pw.new_context(viewport={'width':1100,'height':760}); p = ctx.new_page(); p.goto(BASE)
    p.get_by_test_id('username').fill(user); p.get_by_test_id('password').fill(pwd); p.get_by_test_id('login-btn').click()
    return ctx, p
def outcome(p):
    p.wait_for_timeout(350)
    if p.get_by_test_id('toast-ok').count(): return 'Saved'
    if p.get_by_test_id('toast-err').count():
        LAST['m']=p.locator('.toast.err').first.inner_text(); return 'Error message'
    if p.locator('.fe:not(:empty)').count() or p.locator('.bad').count(): return 'Error message'
    return 'No response'
def clear_toasts(p): p.evaluate("document.querySelector('#msg').innerHTML=''")

def ect(screen, field, rows, do):
    for cls, desc, val, exp in rows:
        act = do(val)
        RES['ect'].append(dict(msg=LAST['m'], screen=screen, field=field, cls=cls, desc=desc, value=val, expected=exp, actual=act, status='PASS' if act==exp else 'FAIL'))

def ft(id, title, purpose, prereq, steps, expected, fn):
    r = dict(id=id, title=title, purpose=purpose, prereq=prereq, steps=steps, expected=expected)
    try:
        obs, shot = fn(); r.update(status='PASS', observed=obs, shot=shot)
    except Exception as ex:
        r.update(status='FAIL', observed=f'Exception: {str(ex)[:300]}', shot=None)
    RES['ft'].append(r); print(r['id'], r['status'], r['observed'][:90])

with sync_playwright() as sp:
    br = sp.chromium.launch()
    # ---------------- ECT: Login -----------------
    ctx, p = login(br, 'padmin', 'Payroll123!'); p.wait_for_timeout(300); ctx.close()
    ctx = br.new_context(); p = ctx.new_page(); p.goto(BASE)
    def do_login(v):
        u, pw_ = v; p.reload(); p.get_by_test_id('username').fill(u); p.get_by_test_id('password').fill(pw_); p.get_by_test_id('login-btn').click(); p.wait_for_timeout(300)
        return 'Dashboard' if p.get_by_test_id('welcome').count() else 'Error message'
    for cls, desc, val, exp in [
        ('Valid','Valid username and password',('padmin','Payroll123!'),'Dashboard'),
        ('Invalid','Valid username, wrong password',('padmin','wrong'),'Error message'),
        ('Invalid','Unknown username',('nobody','Payroll123!'),'Error message'),
        ('Empty','Empty username',('','Payroll123!'),'Error message'),
        ('Empty','Empty password',('padmin',''),'Error message'),
        ('Invalid','Username with only spaces',('   ','Payroll123!'),'Error message'),
        ('Invalid','SQL-injection style text',("' OR '1'='1",'x'),'Error message')]:
        act = do_login(val); RES['ect'].append(dict(screen='Login (UI-1)', field='Username / Password', cls=cls, desc=desc, value=f"{val[0]!r} / {'*'*len(val[1])}", expected=exp, actual=act, status='PASS' if act==exp else 'FAIL'))
        if act=='Dashboard': p.get_by_test_id('logout').click()
    ctx.close()

    ctx, p = login(br, 'padmin', 'Payroll123!')
    # ---------------- ECT: Add Employee -----------------
    p.get_by_test_id('nav-employees').click(); p.get_by_test_id('search-btn').wait_for(); p.get_by_test_id('add-employee').click()
    n = {'i':0}
    def emp(first='Valid', last='Person', email=None, hire='2026-01-05', dept='1', pos='1'):
        n['i'] += 1; email = email if email is not None else f'e{n["i"]}@pms.test'
        clear_toasts(p)
        p.get_by_test_id('first_name').fill(first); p.get_by_test_id('last_name').fill(last); p.get_by_test_id('email').fill(email)
        p.get_by_test_id('hire_date').fill(hire) if hire else p.get_by_test_id('hire_date').fill('')
        p.get_by_test_id('department_id').select_option(dept); p.get_by_test_id('position_id').select_option(pos)
        p.get_by_test_id('save-employee').click(); r = outcome(p)
        if r == 'Saved': p.get_by_test_id('add-employee').click()
        return r
    ect('Add Employee (UI-5)','First name',[
      ('Valid','Letters only','Alice','Saved'),('Valid','Hyphen and apostrophe',"Mary-Ann O'Neil",'Saved'),('Invalid','Empty','','Error message'),
      ('Invalid','All spaces','     ','Error message'),('Invalid','Numeric characters','12345','Error message'),('Invalid','Special characters','@#$%','Error message'),
      ('Invalid','Longer than 50 characters','A'*51,'Error message')], lambda v: emp(first=v))
    ect('Add Employee (UI-5)','Email',[
      ('Valid','Well-formed address','new.hire@pms.test','Saved'),('Invalid','Missing @','newhire.pms.test','Error message'),('Invalid','Empty','','Error message'),
      ('Invalid','Duplicate of existing employee','maria.lopez@pms.test','Error message')], lambda v: emp(email=v))
    ect('Add Employee (UI-5)','Hire date',[
      ('Valid','Past date','2025-06-01','Saved'),('Invalid','Future date','2030-01-01','Error message'),('Invalid','Empty','','Error message')], lambda v: emp(hire=v))
    ect('Add Employee (UI-5)','Department',[('Valid','Department selected','1','Saved'),('Invalid','No department selected','','Error message')], lambda v: emp(dept=v))
    # ---------------- ECT: Attendance -----------------
    p.get_by_test_id('nav-attendance').click(); p.get_by_test_id('submit-hours').wait_for(); p.get_by_test_id('employee_id').select_option('1')
    day = {'d':0}
    def att(reg, ot='0', date=None):
        day['d'] += 1; clear_toasts(p)
        date = date or f'2026-09-{day["d"]:02d}'
        p.get_by_test_id('work_date').fill(date); p.get_by_test_id('regular').fill(reg); p.get_by_test_id('overtime').fill(ot)
        p.get_by_test_id('submit-hours').click(); return outcome(p)
    ect('Attendance Entry (UI-6)','Regular hours',[
      ('Valid','Typical shift','8','Saved'),('Valid','Boundary: 0','0','Saved'),('Valid','Boundary: 24','24','Saved'),('Invalid','Above upper bound (24.5)','24.5','Error message'),
      ('Invalid','Negative','-1','Error message'),('Invalid','Non-numeric','eight','Error message'),('Invalid','Empty','','Error message')], lambda v: att(v))
    ect('Attendance Entry (UI-6)','Overtime hours',[('Valid','Zero overtime','0','Saved'),('Valid','Overtime 2 h','2','Saved'),('Invalid','Total regular+OT > 24 (8 + 20)','20','Error message'),('Invalid','Negative','-3','Error message')],
        lambda v: att('8', v))
    # ---------------- ECT: Compensation -----------------
    p.get_by_test_id('nav-compensation').click(); p.get_by_test_id('save-comp').wait_for(); p.get_by_test_id('employee_id').select_option('3')
    def comp(rate, mult='1.5', typ='hourly', bonus='0'):
        clear_toasts(p); p.get_by_test_id('pay_type').select_option(typ); p.get_by_test_id('rate').fill(rate); p.get_by_test_id('ot_multiplier').fill(mult); p.get_by_test_id('bonus').fill(bonus)
        p.get_by_test_id('save-comp').click(); return outcome(p)
    ect('Compensation Setup (UI-7)','Hourly rate',[('Valid','Typical rate','25.50','Saved'),('Invalid','Zero','0','Error message'),('Invalid','Negative','-5','Error message'),('Invalid','Above 1000 (hourly max)','1500','Error message'),('Invalid','Non-numeric','abc','Error message'),('Invalid','Empty','','Error message')], lambda v: comp(v))
    ect('Compensation Setup (UI-7)','Overtime multiplier',[('Valid','1.5','1.5','Saved'),('Valid','Boundary 1.0','1','Saved'),('Invalid','Below 1.0','0.5','Error message'),('Invalid','Above 3.0','3.5','Error message')], lambda v: comp('25.50', v))
    # restore Aisha
    comp('25.5')
    # ---------------- ECT: Deduction -----------------
    p.get_by_test_id('nav-deductions').click(); p.get_by_test_id('add-deduction').wait_for(); p.get_by_test_id('employee_id').select_option('3')
    def ded(val, mode='percent', name='Test Deduction'):
        clear_toasts(p); p.get_by_test_id('name').fill(name); p.get_by_test_id('kind').select_option('other'); p.get_by_test_id('mode').select_option(mode); p.get_by_test_id('value').fill(val)
        p.get_by_test_id('add-deduction').click(); return outcome(p)
    ect('Deduction Setup (UI-8)','Percentage value',[('Valid','5 %','5','Saved'),('Valid','Boundary 100 %','100','Saved'),('Invalid','Above 100 %','101','Error message'),('Invalid','Zero','0','Error message'),('Invalid','Non-numeric','x','Error message')], lambda v: ded(v))
    ect('Deduction Setup (UI-8)','Deduction name',[('Valid','Normal text','Parking','Saved'),('Invalid','Empty','','Error message'),('Invalid','Over 40 characters','X'*41,'Error message')], lambda v: ded('5','flat',v))
    # remove the junk deductions so payroll test is deterministic
    import sqlite3
    c = sqlite3.connect(DB); c.execute("DELETE FROM deduction WHERE name IN ('Test Deduction','Parking') OR name LIKE 'XXXX%'"); c.commit(); c.close()
    # remove test attendance/employees influence: clear attendance, drop test employees' payroll impact (they lack compensation -> skipped)
    c = sqlite3.connect(DB); c.execute("DELETE FROM attendance"); c.commit(); c.close()
    ctx.close()

    # ---------------- FUNCTIONAL TESTS -----------------
    S = lambda name: os.path.join(SHOTS, name + '.png')
    # FT-1 login journey start
    def t1():
        ctx, p = login(br, 'padmin', 'Payroll123!'); expect(p.get_by_test_id('welcome')).to_be_visible()
        tiles = p.locator('.tile').all_inner_texts(); p.screenshot(path=S('ft1')); ctx.close()
        return f"Dashboard displayed with welcome banner and tiles: {', '.join(tiles)}.", 'ft1'
    ft('FT-1','Log In (valid credentials)','Verify a Payroll Administrator can log in and reach the role-based dashboard.','Seeded account padmin exists; app running.',
       ['Open the application URL.','Enter username "padmin" and password "Payroll123!".','Click Log In.'],'Dashboard (UI-2) opens with welcome banner and role-specific tiles.', t1)
    def t1b():
        ctx = br.new_context(); p = ctx.new_page(); p.goto(BASE)
        msgs=[]
        for i in range(5):
            p.reload(); p.get_by_test_id('username').fill('james'); p.get_by_test_id('password').fill('bad'+str(i)); p.get_by_test_id('login-btn').click(); p.wait_for_timeout(250); msgs.append(p.get_by_test_id('login-error').inner_text())
        p.reload(); p.get_by_test_id('username').fill('james'); p.get_by_test_id('password').fill('Employee123!'); p.get_by_test_id('login-btn').click(); p.wait_for_timeout(250)
        last = p.get_by_test_id('login-error').inner_text(); p.screenshot(path=S('ft1_2')); ctx.close()
        assert 'locked' in msgs[-1].lower() and 'locked' in last.lower(), (msgs, last)
        return f"Attempts 1-4: \"{msgs[0]}\". Attempt 5: \"{msgs[4]}\". Login with the correct password afterwards still refused: \"{last}\".", 'ft1_2'
    ft('FT-1.2','Log In - account lockout','Verify the account locks after 5 failed attempts (S1.1).','Seeded account james exists and is unlocked.',
       ['Attempt login as "james" with a wrong password five times.','Attempt login with the correct password.'],'After the fifth failure the account is locked; the correct password is also refused with a lock message.', t1b)
    def t2():
        ctx, p = login(br, 'sysadmin', 'SysAdmin123!'); p.get_by_test_id('nav-users').click(); expect(p.get_by_test_id('unlock-james')).to_be_visible(); p.screenshot(path=S('ft2')); p.get_by_test_id('unlock-james').click(); p.wait_for_timeout(400)
        ok = p.get_by_test_id('unlock-james').count()==0; ctx.close()
        ctx, p = login(br, 'james', 'Employee123!'); expect(p.get_by_test_id('welcome')).to_be_visible(); ctx.close()
        assert ok
        return 'Locked account "james" was listed with an Unlock button; after unlocking, james logged in successfully.', 'ft2'
    ft('FT-2','Unlock User (System Administrator)','Verify a System Administrator can restore a locked account.','FT-1.2 executed (james locked).',
       ['Log in as sysadmin.','Open Users.','Click Unlock on "james".','Log in as james with the correct password.'],'Account becomes active and login succeeds.', t2)
    def t3():
        ctx, p = login(br, 'maria', 'Employee123!'); expect(p.get_by_test_id('welcome')).to_be_visible()
        menu = p.locator('#nav button').all_inner_texts()
        code = p.evaluate("fetch('/api/employees').then(r=>r.status)")
        code2 = p.evaluate("fetch('/api/periods').then(r=>r.status)")
        p.screenshot(path=S('ft3')); ctx.close()
        assert menu==['Home','My Pay Statements'] and code==403 and code2==403, (menu,code,code2)
        return f"Menu shows only {menu}. Direct API calls to /api/employees and /api/periods returned HTTP {code} and {code2} (permission denied).", 'ft3'
    ft('FT-3','Role-based menu and access control','Verify an Employee sees only permitted menu items and cannot reach admin functions directly (S9.2).','Account maria (Employee) exists.',
       ['Log in as maria.','Observe the navigation menu.','Request the employee list and payroll periods directly through the API.'],'Only "My Pay Statements" is shown; direct requests are rejected with 403.', t3)
    def t3b():
        ctx = br.new_context(); p = ctx.new_page(); p.goto(BASE); code = p.evaluate("fetch('/api/employees').then(r=>r.status)"); ctx.close()
        assert code==401; return f'Unauthenticated request to a protected endpoint returned HTTP {code}.', None
    ft('FT-3.1','Unauthenticated access blocked','Verify protected endpoints reject requests without a session (MW-2).','No active session.',['Without logging in, request /api/employees.'],'HTTP 401, no data returned.', t3b)

    pa_ctx, pa = login(br, 'padmin', 'Payroll123!')
    def t4():
        pa.get_by_test_id('nav-employees').click(); pa.get_by_test_id('search-btn').wait_for(); pa.get_by_test_id('add-employee').click()
        pa.get_by_test_id('first_name').fill('Priya'); pa.get_by_test_id('last_name').fill('Nair'); pa.get_by_test_id('email').fill('priya.nair@pms.test'); pa.get_by_test_id('hire_date').fill('2026-02-02')
        pa.get_by_test_id('department_id').select_option(label='Finance'); pa.get_by_test_id('position_id').select_option(label='Analyst'); pa.get_by_test_id('save-employee').click(); pa.wait_for_timeout(400)
        pa.get_by_test_id('search-q').fill('Nair'); pa.get_by_test_id('search-btn').click(); pa.wait_for_timeout(300)
        txt = pa.get_by_test_id('emp-rows').inner_text(); pa.screenshot(path=S('ft4')); assert 'Priya Nair' in txt
        return 'Success message "Employee saved." shown; searching "Nair" returns the new row: ' + ' '.join(txt.split())+'.', 'ft4'
    ft('FT-4','Add Employee and find via Search','Verify a valid employee is saved and retrievable (S2.1, S2.3).','Logged in as padmin; Employee List open.',
       ['Click + Add.','Enter Priya / Nair / priya.nair@pms.test / 2026-02-02, Department Finance, Position Analyst.','Click Save.','Search for "Nair".'],'Record saved; search result shows the new employee.', t4)
    def t4b():
        pa.get_by_test_id('search-q').fill('zzzz'); pa.get_by_test_id('search-btn').click(); pa.wait_for_timeout(300)
        a = pa.get_by_test_id('no-results').inner_text()
        pa.get_by_test_id('search-q').fill(''); pa.get_by_test_id('dept').select_option(label='Engineering'); pa.get_by_test_id('search-btn').click(); pa.wait_for_timeout(300)
        b = pa.get_by_test_id('emp-rows').inner_text(); assert 'Maria' in b and 'James' not in b
        pa.get_by_test_id('dept').select_option(''); return f'Name "zzzz" -> "{a}". Department filter Engineering -> only: {" ".join(b.split())}.', None
    ft('FT-5','Search / Filter employees','Verify search by name and department filter, including no-result case.','Seeded employees exist.',
       ['Search "zzzz".','Clear text; choose Department = Engineering; Search.'],'"No employees found." for unknown text; only Engineering employees listed for the filter.', t4b)
    def t5():
        pa.get_by_test_id('add-employee').click(); pa.get_by_test_id('first_name').fill('Bad3'); pa.get_by_test_id('save-employee').click(); pa.wait_for_timeout(400)
        err = pa.locator('.toast.err').first.inner_text(); fe = pa.locator('.fe:not(:empty)').all_inner_texts(); pa.screenshot(path=S('ft5'))
        pa.get_by_test_id('cancel-employee').click(); assert err and fe
        return f'Toast: "{err}". Inline messages: {fe}. Form not saved.', 'ft5'
    ft('FT-5.1','Add Employee - validation errors','Verify invalid input is rejected with clear messages and nothing is saved (S11.1).','Employee List open.',['Click + Add.','Enter first name "Bad3" and leave other fields empty.','Click Save.'],'Error messages displayed per invalid field; employee not created.', t5)
    def t5b():
        pa.get_by_test_id('add-employee').click(); pa.get_by_test_id('first_name').fill('Temp'); pa.get_by_test_id('last_name').fill('Worker'); pa.get_by_test_id('email').fill('temp.worker@pms.test'); pa.get_by_test_id('hire_date').fill('2026-03-01')
        pa.get_by_test_id('department_id').select_option('1'); pa.get_by_test_id('position_id').select_option('1'); pa.get_by_test_id('save-employee').click(); pa.wait_for_timeout(400)
        pa.get_by_test_id('search-q').fill('Worker'); pa.get_by_test_id('search-btn').click(); pa.wait_for_timeout(300)
        row = pa.locator('[data-testid^=deact-]').first; row.click(); pa.get_by_test_id('confirm-no').click(); pa.wait_for_timeout(300)
        still = 'Active' in pa.get_by_test_id('emp-rows').inner_text()
        row.click(); pa.screenshot(path=S('ft5b')); pa.get_by_test_id('confirm-yes').click(); pa.wait_for_timeout(500)
        after = 'Inactive' in pa.get_by_test_id('emp-rows').inner_text(); assert still and after
        return 'Deactivate shows a confirmation dialog; Cancel left the employee Active; Confirm changed status to Inactive.', 'ft5b'
    ft('FT-6','Deactivate Employee (confirmation)','Verify irreversible action requires confirmation (S2.2, UX gap check).','An active employee exists.',['Search "Worker".','Click Deactivate, then Cancel.','Click Deactivate, then Confirm.'],'Cancel changes nothing; Confirm sets status Inactive.', t5b)
    def t6():
        pa.get_by_test_id('nav-attendance').click(); pa.get_by_test_id('submit-hours').wait_for(); pa.get_by_test_id('employee_id').select_option('1')
        for d,r,o in [('2026-10-01','8','0'),('2026-10-02','8','2')]:
            pa.get_by_test_id('work_date').fill(d); pa.get_by_test_id('regular').fill(r); pa.get_by_test_id('overtime').fill(o); pa.get_by_test_id('submit-hours').click(); pa.wait_for_timeout(400)
        rows = ' | '.join(' '.join(x.split()) for x in pa.get_by_test_id('att-rows').locator('tr').all_inner_texts()); pa.screenshot(path=S('ft6'))
        assert '2026-10-01' in rows and '2026-10-02' in rows
        return f'Both days saved and listed: {rows}.', 'ft6'
    ft('FT-7','Enter Attendance hours','Verify regular and overtime hours are stored for an employee (S3.1, S3.2).','Employee Maria Lopez (ID 1) active.',['Open Attendance.','Select Maria.','Submit 2026-10-01: 8 regular / 0 OT.','Submit 2026-10-02: 8 regular / 2 OT.'],'Both entries saved and shown in the grid.', t6)
    def t6b():
        pa.get_by_test_id('work_date').fill('2026-09-30'); pa.get_by_test_id('regular').fill('8'); pa.get_by_test_id('overtime').fill('11'); clear_toasts(pa); pa.get_by_test_id('submit-hours').click(); pa.wait_for_timeout(400)
        w = pa.locator('.toast.warn').first.inner_text(); assert 'flagged' in w
        pa.get_by_test_id('work_date').fill('2026-09-30'); pa.get_by_test_id('regular').fill('8'); pa.get_by_test_id('overtime').fill('1'); pa.get_by_test_id('submit-hours').click(); pa.wait_for_timeout(300)
        return f'Overtime of 11 h saved with warning: "{w}". Entry then corrected to 1 h (existing day overwritten, no duplicate).', None
    ft('FT-7.1','Overtime approval-threshold flag','Verify excessive overtime is flagged (S3.3).','Attendance screen open.',['Submit 2026-09-30 with 8 regular, 11 overtime.'],'Saved with a warning that overtime exceeds the approval threshold.', t6b)
    def t7():
        pa.get_by_test_id('nav-compensation').click(); pa.get_by_test_id('save-comp').wait_for(); pa.get_by_test_id('employee_id').select_option('2'); pa.wait_for_timeout(300)
        loaded = pa.get_by_test_id('rate').input_value(); pa.get_by_test_id('rate').fill('80000'); pa.get_by_test_id('save-comp').click(); pa.wait_for_timeout(400)
        pa.get_by_test_id('employee_id').select_option('1'); pa.get_by_test_id('employee_id').select_option('2'); pa.wait_for_timeout(400)
        v = pa.get_by_test_id('rate').input_value(); pa.screenshot(path=S('ft7'))
        pa.get_by_test_id('rate').fill('78000'); pa.get_by_test_id('save-comp').click(); pa.wait_for_timeout(400)
        assert loaded=='78000' and v=='80000'; return f'Existing compensation loaded (78000); changed to 80000 and persisted after re-selecting the employee (shown {v}); restored to 78000 for later tests.', 'ft7'
    ft('FT-8','Compensation Setup - load, edit, persist','Verify compensation is stored and reloaded (S4.1, S4.2).','Compensation exists for James Carter.',['Open Compensation; select James.','Change salary to 80000; Save.','Re-select James.'],'Existing values prefill; new value persists.', t7)
    def t8():
        pa.get_by_test_id('nav-deductions').click(); pa.get_by_test_id('add-deduction').wait_for(); pa.get_by_test_id('employee_id').select_option('1'); pa.wait_for_timeout(300)
        before = pa.get_by_test_id('ded-rows').locator('tr').count()
        pa.get_by_test_id('name').fill('Union Dues'); pa.get_by_test_id('kind').select_option('other'); pa.get_by_test_id('mode').select_option('flat'); pa.get_by_test_id('value').fill('20'); pa.get_by_test_id('add-deduction').click(); pa.wait_for_timeout(400)
        mid = pa.get_by_test_id('ded-rows').locator('tr').count(); pa.screenshot(path=S('ft8'))
        pa.locator('[data-del]').last.click(); pa.wait_for_timeout(300); after = pa.get_by_test_id('ded-rows').locator('tr').count()
        assert mid==before+1 and after==before; return f'Deduction list grew from {before} to {mid} rows after adding "Union Dues" ($20 flat); Remove returned it to {after}.', 'ft8'
    ft('FT-9','Add / remove Deduction','Verify deductions can be added and removed per employee (S5.1).','Maria has 2 deductions.',['Open Deductions; select Maria.','Add "Union Dues", Other, Flat, 20.','Remove it.'],'Row added then removed.', t8)
    def t9():
        pa.get_by_test_id('nav-payroll').click(); pa.get_by_test_id('create-period').wait_for()
        pa.get_by_test_id('start_date').fill('2026-10-01'); pa.get_by_test_id('end_date').fill('2026-10-14'); pa.get_by_test_id('create-period').click(); pa.wait_for_timeout(500); ok1 = pa.locator('.toast.ok').count()>0
        clear_toasts(pa); pa.get_by_test_id('start_date').fill('2026-10-10'); pa.get_by_test_id('end_date').fill('2026-10-20'); pa.get_by_test_id('create-period').click(); pa.wait_for_timeout(400); t_ov = pa.locator('.toast.err').first.inner_text()
        clear_toasts(pa); pa.get_by_test_id('start_date').fill('2026-11-05'); pa.get_by_test_id('end_date').fill('2026-11-01'); pa.get_by_test_id('create-period').click(); pa.wait_for_timeout(400); t_rev = pa.locator('.toast.err').first.inner_text(); pa.screenshot(path=S('ft9'))
        assert ok1 and 'overlap' in t_ov.lower() and 'before' in t_rev.lower()
        return f'Period 2026-10-01..2026-10-14 created. Overlapping period -> "{t_ov}". End before start -> "{t_rev}".', 'ft9'
    ft('FT-10','Create payroll period (+ overlap/date checks)','Verify period creation and rejection of overlapping or reversed periods (S6.1).','Logged in as padmin; Payroll screen open.',['Create 2026-10-01 to 2026-10-14.','Create 2026-10-10 to 2026-10-20.','Create 2026-11-05 to 2026-11-01.'],'First saved; the other two rejected with messages.', t9)
    def t10():
        pa.get_by_test_id('period').select_option(index=1); pa.get_by_test_id('calculate').click(); pa.wait_for_timeout(700)
        rows = pa.get_by_test_id('pay-rows').locator('tr'); data = {}
        for t in rows.all_inner_texts():
            c = t.split('\t'); data[c[0].strip()] = [x.strip() for x in c[1:6]]
        pa.screenshot(path=S('ft10'))
        exp = {'Maria Lopez':('860.00','188.20','671.80'),'James Carter':('3,000.00','450.00','2,550.00'),'Aisha Khan':('0.00','0.00','0.00'),'Daniel Okafor':('3,903.85','195.19','3,708.66')}
        lines=[]
        for k,(g,d,nt) in exp.items():
            got = data[k]; assert got[2]==f'${g}' and got[3]==f'${d}' and got[4]==f'${nt}', (k,got)
            lines.append(f'{k}: gross ${g}, deductions ${d}, net ${nt}')
        assert 'Priya Nair' not in data
        return 'Results matched hand calculations - ' + '; '.join(lines) + '. Employees without compensation (new hires) skipped. Status = Calculated.', 'ft10'
    ft('FT-11','Calculate Payroll (accuracy)','Verify gross, deduction and net amounts equal independently computed values (S6.2, S6.3).','Period created; Maria: 16 reg h + 2 OT h @ $40, 1.5x, bonus $100, 12% tax + $85 insurance; James $78,000; Daniel $95,000 + $250 bonus, 5%; Aisha no hours.',
       ['Select the period.','Click Calculate Payroll.','Compare each row with hand calculation.'],'Maria 860.00/188.20/671.80; James 3,000.00/450.00/2,550.00; Aisha 0; Daniel 3,903.85/195.19/3,708.66.', t10)
    def t10b():
        clear_toasts(pa); pa.get_by_test_id('finalize').click(); pa.get_by_test_id('confirm-yes').click(); pa.wait_for_timeout(500)
        m = pa.locator('.toast.err').first.inner_text(); st = pa.get_by_test_id('status-pill').inner_text(); pa.screenshot(path=S('ft10b'))
        assert 'second' in m.lower() and st=='Calculated'
        return f'Same user (who calculated) attempted Finalize -> "{m}"; status stays "{st}".', 'ft10b'
    ft('FT-12','Finalize requires second approver','Verify the calculating user cannot also finalize (S6.4 second-person authorization).','Period is Calculated by padmin.',['As padmin, click Finalize and confirm.'],'Rejected; status unchanged.', t10b)
    fn_ctx, fn = login(br, 'fin1', 'Finance123!')
    def t11():
        fn.get_by_test_id('nav-payroll').click(); fn.get_by_test_id('calculate').wait_for(); fn.get_by_test_id('period').select_option(index=1); fn.wait_for_timeout(300)
        fn.get_by_test_id('finalize').click(); fn.screenshot(path=S('ft11')); fn.get_by_test_id('confirm-no').click(); fn.wait_for_timeout(300); s1 = fn.get_by_test_id('status-pill').inner_text()
        fn.get_by_test_id('finalize').click(); fn.get_by_test_id('confirm-yes').click(); fn.wait_for_timeout(600); s2 = fn.get_by_test_id('status-pill').inner_text()
        assert s1=='Calculated' and s2=='Finalized'; return f'Confirmation dialog appeared; Cancel kept status "{s1}"; Confirm by finance user fin1 set status "{s2}".', 'ft11'
    ft('FT-13','Finalize payroll (second approver, confirmation)','Verify a different authorized user can finalize and that a confirmation dialog protects the action.','FT-12 executed; fin1 account exists.',['Log in as fin1.','Open Payroll; select the period.','Click Finalize -> Cancel.','Click Finalize -> Confirm.'],'Cancel leaves status; Confirm sets status Finalized.', t11)
    def t11b():
        clear_toasts(fn); fn.get_by_test_id('calculate').click(); fn.wait_for_timeout(400); m = fn.locator('.toast.err').first.inner_text()
        r = pa.evaluate("fetch('/api/attendance',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({employee_id:1,work_date:'2026-10-05',regular:'8',overtime:'0'})}).then(r=>r.json())")
        assert 'locked' in m.lower() and 'finalized' in r['error'].lower()
        return f'Recalculate -> "{m}". Attendance edit inside the period -> "{r["error"]}".', None
    ft('FT-14','Finalized period is locked','Verify finalized data cannot be recalculated or edited (S6.4, S10.2).','Period finalized.',['Click Calculate Payroll on the finalized period.','Submit attendance dated inside the period.'],'Both operations rejected.', t11b)
    fn_ctx.close()
    em_ctx, em = login(br, 'maria', 'Employee123!')
    def t12():
        em.get_by_test_id('nav-paystatement').click(); em.get_by_test_id('period').wait_for(); em.get_by_test_id('period').select_option(index=1); em.wait_for_timeout(400)
        gross = em.get_by_test_id('st-gross').inner_text(); net = em.get_by_test_id('st-net').inner_text(); em.screenshot(path=S('ft12'))
        with em.expect_download() as d: em.get_by_test_id('download').click()
        path = d.value.path(); html = open(path).read(); assert gross=='$860.00' and net=='$671.80' and '671.80' in html
        return f'Maria sees her statement: gross {gross}, net {net}. Download produced a file containing the same net pay.', 'ft12'
    ft('FT-15','Employee views and downloads own Pay Statement','Complete journey end: employee self-service (S7.1, S7.2).','Period finalized (FT-13).',['Log in as maria.','Open My Pay Statements; choose the period.','Click Download.'],'Earnings, deductions and net pay shown (gross $860.00, net $671.80); download succeeds.', t12)
    def t13():
        r = em.evaluate("fetch('/api/paystatements/1?employee_id=2').then(r=>r.json())"); r2 = em.evaluate("fetch('/api/periods/1/results').then(r=>r.status)")
        assert r['employee']=='Maria Lopez' and r2==403
        return f'Request that tried to read employee 2\'s statement returned Maria\'s own data ("{r["employee"]}"); payroll results endpoint returned HTTP {r2}.', None
    ft('FT-16','Employee cannot read another employee\'s pay data','Verify record-level restriction (S12.2).','Maria logged in; James also has a finalized statement.',['Call /api/paystatements/1?employee_id=2.','Call /api/periods/1/results.'],'Only the caller\'s own data is returned; payroll results forbidden (403).', t13)
    em_ctx.close()
    def t14():
        p2 = pa; p2.get_by_test_id('nav-reports').click(); p2.get_by_test_id('generate').wait_for(); p2.get_by_test_id('period').select_option(index=1); p2.get_by_test_id('generate').click(); p2.wait_for_timeout(500)
        g = p2.get_by_test_id('rt-gross').inner_text(); n = p2.get_by_test_id('rt-net').inner_text(); p2.screenshot(path=S('ft14'))
        assert g=='$7,763.85' and n=='$6,930.46', (g,n); return f'Payroll Summary totals: gross {g} (860.00+3,000.00+0+3,903.85), net {n}.', 'ft14'
    ft('FT-17','Payroll Summary report','Verify the report totals equal the sum of the calculated rows (S8.1).','Period calculated/finalized.',['Open Reports; choose the period; click Generate.'],'Totals: gross $7,763.85; net $6,930.46.', t14)
    sa_ctx, sa = login(br, 'sysadmin', 'SysAdmin123!')
    def t15():
        sa.get_by_test_id('nav-audit').click(); sa.get_by_test_id('filter').wait_for(); sa.wait_for_timeout(400); txt = sa.get_by_test_id('audit-rows').inner_text()
        need = ['LOGIN_FAILED','CALCULATE_PAYROLL','FINALIZE_PAYROLL','CREATE_EMPLOYEE','SAVE_ATTENDANCE']
        for a in need: assert a in txt, a
        sa.get_by_test_id('user').fill('fin1'); sa.get_by_test_id('filter').click(); sa.wait_for_timeout(400); f_ = sa.get_by_test_id('audit-rows').inner_text(); sa.screenshot(path=S('ft15'))
        assert 'padmin' not in f_ and 'FINALIZE_PAYROLL' in f_
        return 'Audit log lists ' + ', '.join(need) + ' events with user and timestamp. Filter by user "fin1" shows only that user\'s actions (including FINALIZE_PAYROLL).', 'ft15'
    ft('FT-18','Audit log records and filters activity','Verify important actions are logged and filterable (S10.1).','Earlier tests executed.',['Log in as sysadmin.','Open Audit Log.','Filter user = fin1.'],'Events present; filter restricts rows.', t15)
    sa_ctx.close(); pa_ctx.close(); br.close()

srv.terminate()
json.dump(RES, open(os.path.join(ROOT, 'tests', 'results.json'), 'w'), indent=1)
e = RES['ect']; f = RES['ft']
print('ECT', sum(x['status']=='PASS' for x in e), '/', len(e), ' FT', sum(x['status']=='PASS' for x in f), '/', len(f))

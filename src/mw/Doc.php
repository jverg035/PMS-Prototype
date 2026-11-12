<?php
// MW-8 Document Generation Service (prototype renders a downloadable HTML statement; production would emit PDF).
class Doc {
  static function statement(array $s): string {
    $e = fn($x) => htmlspecialchars((string)$x);
    $rows = ''; foreach ($s['deductions'] as $d) $rows .= "<tr><td>{$e($d['name'])}</td><td align=right>$".number_format($d['amount'],2)."</td></tr>";
    return "<!doctype html><meta charset=utf-8><title>Pay Statement</title><body style='font-family:Arial;max-width:560px;margin:30px auto'>
<h2>Pay Statement</h2><p><b>{$e($s['employee'])}</b><br>Period: {$e($s['period'])}</p>
<table width=100% border=1 cellpadding=6 style='border-collapse:collapse'>
<tr><th align=left colspan=2>Earnings</th></tr>
<tr><td>Regular ({$s['regular_hours']} h)</td><td align=right>$".number_format($s['regular_pay'],2)."</td></tr>
<tr><td>Overtime ({$s['overtime_hours']} h)</td><td align=right>$".number_format($s['overtime_pay'],2)."</td></tr>
<tr><td>Bonus</td><td align=right>$".number_format($s['bonus'],2)."</td></tr>
<tr><td><b>Gross</b></td><td align=right><b>$".number_format($s['gross'],2)."</b></td></tr>
<tr><th align=left colspan=2>Deductions</th></tr>$rows
<tr><td><b>Net Pay</b></td><td align=right><b>$".number_format($s['net'],2)."</b></td></tr></table></body>";
  }
  static function csv(array $rows): string { $h = fopen('php://temp','r+'); foreach ($rows as $r) fputcsv($h, $r); rewind($h); return stream_get_contents($h); }
}

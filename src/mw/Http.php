<?php
// MW-1 helpers (JSON in/out) + MW-4 Validation & Message Service.
class Http {
  static function body(): array { $j = json_decode(file_get_contents('php://input'), true); return is_array($j) ? $j : []; }
  static function out($data, int $code = 200) { http_response_code($code); header('Content-Type: application/json'); echo json_encode($data); exit; }
  static function fail(string $msg, int $code = 400, array $fields = []) { self::out(['error' => $msg, 'fields' => $fields], $code); }
}
class Validate { // MW-4
  static function name($v, $label) {
    $v = trim((string)$v);
    if ($v === '') return "$label is required.";
    if (mb_strlen($v) > 50) return "$label must be 50 characters or fewer.";
    if (!preg_match("/^[A-Za-z][A-Za-z '\-]*$/", $v)) return "$label may contain letters, spaces, hyphens and apostrophes only.";
    return null;
  }
  static function email($v) {
    $v = trim((string)$v);
    if ($v === '') return 'Email is required.';
    if (mb_strlen($v) > 100 || !filter_var($v, FILTER_VALIDATE_EMAIL)) return 'Enter a valid email address.';
    return null;
  }
  static function date($v, $label, $notFuture = false) {
    $v = trim((string)$v);
    if ($v === '') return "$label is required.";
    $d = DateTime::createFromFormat('Y-m-d', $v);
    if (!$d || $d->format('Y-m-d') !== $v) return "$label must be a valid date (YYYY-MM-DD).";
    if ($notFuture && $v > date('Y-m-d')) return "$label cannot be in the future.";
    return null;
  }
  static function num($v, $label, $min, $max, $minExclusive = false) {
    if ($v === '' || $v === null) return "$label is required.";
    if (!is_numeric($v)) return "$label must be a number.";
    $n = (float)$v;
    if ($minExclusive ? $n <= $min : $n < $min) return "$label must be " . ($minExclusive ? 'greater than ' : 'at least ') . "$min.";
    if ($n > $max) return "$label must not exceed $max.";
    return null;
  }
  static function collect(array $errs) { $e = array_filter($errs); if ($e) Http::fail(reset($e), 422, $e); }
}

<?php
// MW-2 Security Filter (session, timeout) and MW-3 Role-Based Authorization.
class Security {
  const TIMEOUT = 1800;
  static function start() { if (session_status() !== PHP_SESSION_ACTIVE) session_start(); }
  static function user() {
    self::start();
    if (empty($_SESSION['u'])) return null;
    if (time() - ($_SESSION['t'] ?? 0) > self::TIMEOUT) { session_destroy(); return null; }
    $_SESSION['t'] = time();
    return $_SESSION['u'];
  }
  static function require(): array { $u = self::user(); if (!$u) Http::fail('Please log in to continue.', 401); return $u; }
  static function login(array $u) { self::start(); session_regenerate_id(true); $_SESSION['u'] = $u; $_SESSION['t'] = time(); }
  static function logout() { self::start(); $_SESSION = []; session_destroy(); }
}
class Authz { // MW-3
  const PAYROLL = ['Payroll Administrator'];
  static function need(array $u, array $roles) {
    if (!in_array($u['role'], $roles, true)) Http::fail('You do not have permission to perform this action.', 403);
  }
}

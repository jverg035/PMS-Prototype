<?php
// MW-7 Audit Event Publisher -> FC-10 store.
class AuditPub {
  static function publish(?array $u, string $action, string $record) {
    Db::run("INSERT INTO audit(ts,user_id,username,action,record) VALUES(?,?,?,?,?)",
      [date('Y-m-d H:i:s'), $u['id'] ?? null, $u['username'] ?? 'anonymous', $action, $record]);
  }
}

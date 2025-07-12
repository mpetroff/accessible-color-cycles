<?php
file_put_contents('log.txt', file_get_contents('php://input') . "\n", FILE_APPEND | LOCK_EX);
?>

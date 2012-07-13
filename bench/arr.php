<?php
function ary($n) {
  $X = array();
  $Y = array();
  for ($i=0; $i<$n; $i++) {
    $X[$i] = $i;
  }
  for ($i=0; $i<$n; $i++) {
    $Y[$i] = $X[$i];
  }
  $last = $n-1;
  //echo $Y[$last], "\n";
}
for ($j = 0; $j < 10; $j += 1) {
  $start = microtime(true);
  for ($i = 0; $i < 10; $i++)
    ary(500000);
  echo microtime(true) - $start, "\n";
}
?>
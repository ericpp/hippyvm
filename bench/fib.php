<?
function fibo_r($n){
    return(($n < 2) ? 1 : fibo_r($n - 2) + fibo_r($n - 1));
}

function fibo($n = 33) {
  $r = fibo_r($n);
  //print "$r\n";
}

for ($i = 0; $i < 10; $i++) {
  $start = microtime(true);
  fibo();
  echo microtime(true) - $start, "\n";
}
?>
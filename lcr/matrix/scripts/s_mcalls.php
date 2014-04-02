#!/usr/bin/php
<?php

$c = new SoapClient('https://mvts-web-service/service/?wsdl', array('timeout' => 1000));

$h = array();
$h[] = new SoapHeader('http://mfisoft.ru/auth', 'Login', 'lcr');
$h[] = new SoapHeader('http://mfisoft.ru/auth', 'Password', 'pass');
$c->__setSoapHeaders($h);

#$t = $c->getTableByTitle('TS CLASS 4 conferences');
$t = '02.2519.01';
#$columns = $c->describeColumns($t);
$records = $c->selectRowset($t, NULL, NULL, 10000);

print_r(json_encode($records));

?>

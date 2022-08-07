# HTTP SEC 

#### 初衷
* 作为最原始的http客户端 我希望能获取到最终发送的内容、也希望能获取最初获取到的内容、但是目前没有公开库对这种需求做了兼容
* 作为网络安全从业者、他们常常会发送一些不符合规则、复杂的url如
```
http://localhost./../api
http://localhost/?doAs=`whoami`
```
无论是request还是urllib3都会进行转义、而更底层的http.client则会直接InvalidURL 而对其源码进行path影响范围不可控



### Send Irregular URL
```
>>> import httpsec
>>> from httpsec import URL
>>> r = httpsec.get(URL(host="testpoc.com",scheme="https",path="./../../",query="doAs=`whoami`"))
>>> r.status_code
200
>>> r.headers['content-type']
'application/json; charset=utf8'
>>> r.encoding
'utf-8'
>>> r.text
'{"authenticated": true, ...'
>>> r.json()
{'authenticated': True, ...}
```


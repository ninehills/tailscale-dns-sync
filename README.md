# tailscale-dns-sync
Sync tailscale hosts to public dns domain.

问题：Tailscale的API Key 有90天的有效期，过期后需要人工修改。

替代方案：目前Tailscale的Magic DNS支持不覆盖Local DNS，所以可以使用 Magic DNS功能。

## Develop

```
$ python3 -m venv ./venv/
$ source venv/bin/activate
$ pip install -r requirements.txt
```

## Config

Copy `config.py.example` to `config.py`, then modify it.


## Baidu Cloud CCE

1. 触发器: `定时任务`, `rate(5 minutes)`
2. 基础信息：
    - 运行时：`Python 3.6`
    - 超时时间: `100` 秒
3. 代码：将`config.py`内容写到文件头，然后将main()写入handler:

```
def handler(event, context): 
    main()
```

# nohup rasa run actions >logs/log/logs_actions.txt 2>&1 & echo $! > logs/pid/actions.pid
# nohup rasa run --enable-api >logs/log/logs_rasa_api.txt 2>&1 & echo $! > logs/pid/rasa_api.pid
nohup python app.py >logs/log/logs.txt 2>&1 & echo $! > logs/pid/run.pid
# nohup python app2.py >logs/log/logs2.txt 2>&1 & echo $! > logs/pid/run2.pid

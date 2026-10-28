import subprocess, sys, time, os

WD = r'D:\Projects\WangHanyu\wanghanyu'
env = dict(os.environ, KIVY_NO_ARGS='1')

p = subprocess.Popen(
    [sys.executable, 'main.py'],
    cwd=WD, env=env,
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    text=True, encoding='utf-8', errors='replace',
)
time.sleep(8)
rc = p.poll()
print('=== exit code:', rc, '===')
if rc is None:
    print('STILL RUNNING -> app stays alive fine')
    p.kill()
else:
    out = p.stdout.read()
    print('--- tail of output ---')
    print('\n'.join(out.splitlines()[-25:]))

import subprocess


def run(cmd, *, cwd=None, env=None, shell=False) -> str:
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        shell=shell,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    print("----- BEGIN COMMAND -----")
    print(cmd if isinstance(cmd, str) else " ".join(cmd))
    print("----- OUTPUT -----")
    print(proc.stdout.rstrip())
    print("----- END COMMAND -----")

    if proc.returncode != 0:
        raise AssertionError(proc.stdout)

    return proc.stdout

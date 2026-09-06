
"""
deploy.py - Build and run the SuperKart backend (Flask) and frontend (Streamlit)
as Docker containers on a shared Docker network inside a GitHub Codespace.

Usage (from the repo root in the Codespace terminal):
    python deploy.py           # build + run both containers
    python deploy.py --stop    # stop and remove containers
"""
import subprocess, sys, time

NETWORK  = "superkart-net"
BACKEND  = {"name": "backend",  "image": "superkart-backend",  "dir": "backend",  "port": 7860}
FRONTEND = {"name": "frontend", "image": "superkart-frontend", "dir": "frontend", "port": 8501}

def run(cmd, check=True):
    print(f"$ {cmd}")
    return subprocess.run(cmd, shell=True, check=check)

def stop():
    for svc in (BACKEND, FRONTEND):
        run(f"docker rm -f {svc['name']}", check=False)
    run(f"docker network rm {NETWORK}", check=False)

def deploy():
    stop()                                                # clean slate
    run(f"docker network create {NETWORK}")
    for svc in (BACKEND, FRONTEND):
        run(f"docker build -t {svc['image']} ./{svc['dir']}")
        run(f"docker run -d --name {svc['name']} --network {NETWORK} "
            f"-p {svc['port']}:{svc['port']} {svc['image']}")
    time.sleep(5)
    run("docker ps")
    print("\nBackend  -> http://localhost:7860   (set port 7860 to PUBLIC in the PORTS tab)")
    print("Frontend -> http://localhost:8501   (open in browser from the PORTS tab)")
    print("Logs     -> docker logs -f backend | docker logs -f frontend")

if __name__ == "__main__":
    stop() if "--stop" in sys.argv else deploy()

#!/usr/bin/env python3
"""
Kiểm tra toàn bộ phần điện toán đám mây trước khi demo: PASS / WARN / FAIL.

Cách dùng:
  python scripts/verify_cloud.py --url http://<node-ip>
  python scripts/verify_cloud.py --url http://<node-ip> --run-backup   # chạy thử sao lưu một lần

Kiểm tra: pod sẵn sàng, HPA, Ingress, đăng nhập và gợi ý, tắt demo mode, NetworkPolicy có hiệu lực,
PodDisruptionBudget, securityContext, CronJob sao lưu. Chỉ dùng thư viện chuẩn của Python.
Thoát với mã 1 nếu có mục FAIL.
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request

NS = "vib-banking"
results = []


def report(status, name, detail=""):
    results.append(status)
    mark = {"PASS": "[PASS]", "WARN": "[WARN]", "FAIL": "[FAIL]"}[status]
    print(f"{mark} {name}" + (f": {detail}" if detail else ""))


def kubectl(*args, timeout=60):
    try:
        r = subprocess.run(["kubectl", *args], capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()
    except FileNotFoundError:
        return 127, "", "không tìm thấy kubectl"
    except subprocess.TimeoutExpired:
        return 124, "", "kubectl quá thời gian chờ"


def http(url, data=None, token=None, timeout=10):
    headers = {}
    if data is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(data).encode()
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return 0, str(e)


def jsonpath(kind, name, path):
    rc, out, err = kubectl("get", kind, name, "-n", NS, "-o", f"jsonpath={path}")
    return (out if rc == 0 else None), err


def main():
    p = argparse.ArgumentParser(description="Kiểm tra cụm VIB-SmartBanking trước khi demo")
    p.add_argument("--url", default="", help="Địa chỉ Ingress, ví dụ http://<node-ip> (bỏ trống thì bỏ qua kiểm tra HTTP)")
    p.add_argument("--customer", default="00992830")
    p.add_argument("--password", default="123456")
    p.add_argument("--run-backup", action="store_true", help="Chạy thử CronJob sao lưu một lần")
    a = p.parse_args()

    rc, out, err = kubectl("get", "namespace", NS)
    if rc != 0:
        report("FAIL", "Kết nối cụm và namespace " + NS, (err.splitlines()[-1] if err else "kubectl lỗi")[:160])
        print("\nKhông kết nối được cụm. Hãy bật K3s rồi chạy scripts/deploy.sh.")
        return 1
    report("PASS", "Kết nối cụm và namespace " + NS)

    # 1. Workload sẵn sàng
    for kind, name in (("deploy", "backend-api"), ("deploy", "frontend-ui"), ("statefulset", "postgres")):
        out, err = jsonpath(kind, name, "{.status.readyReplicas}/{.spec.replicas}")
        if out is None:
            report("FAIL", f"{kind}/{name}", err)
            continue
        ready, _, want = out.partition("/")
        ok = ready not in ("", "0") and ready == want
        report("PASS" if ok else "FAIL", f"{kind}/{name} sẵn sàng", f"{ready or 0}/{want}")

    # 2. HPA
    for name, lo, hi in (("backend-hpa", 2, 8), ("frontend-hpa", 2, 5)):
        out, err = jsonpath("hpa", name, "{.spec.minReplicas}-{.spec.maxReplicas}")
        if out == f"{lo}-{hi}":
            report("PASS", f"hpa/{name}", f"{lo} đến {hi} pod")
        else:
            report("FAIL", f"hpa/{name}", out or err)

    # 3. PodDisruptionBudget
    for name in ("backend-pdb", "frontend-pdb"):
        out, err = jsonpath("pdb", name, "{.spec.minAvailable}")
        report("PASS" if out == "1" else "FAIL", f"pdb/{name}", f"minAvailable={out}" if out else err)

    # 4. Rolling update không gián đoạn
    out, _ = jsonpath("deploy", "backend-api", "{.spec.strategy.rollingUpdate.maxUnavailable}")
    report("PASS" if out == "0" else "WARN", "backend-api cập nhật cuốn chiếu maxUnavailable=0", f"giá trị: {out}")

    # 5. securityContext backend
    out, _ = jsonpath("deploy", "backend-api", "{.spec.template.spec.containers[0].securityContext.allowPrivilegeEscalation}")
    report("PASS" if out == "false" else "WARN", "backend bỏ đặc quyền (allowPrivilegeEscalation=false)", f"giá trị: {out}")

    # 6. HTTP qua Ingress
    if a.url:
        base = a.url.rstrip("/")
        code, _ = http(base + "/ready")
        report("PASS" if code == 200 else "FAIL", "GET /ready qua Ingress", f"mã {code}")
        code, body = http(base + "/api/auth/login", {"customer_number": a.customer, "password": a.password})
        token = ""
        if code == 200:
            try:
                token = json.loads(body)["access_token"]
            except Exception:
                token = ""
        report("PASS" if token else "FAIL", f"Đăng nhập khách {a.customer}", f"mã {code}")
        if token:
            code, _ = http(f"{base}/api/recommendations/{a.customer}", token=token)
            report("PASS" if code == 200 else "FAIL", "Lấy gợi ý AI", f"mã {code}")
            code, _ = http(f"{base}/api/recommendations/00839876", token=token)
            report("PASS" if code == 403 else "FAIL", "Khách này không đọc được dữ liệu khách khác", f"mã {code} (mong đợi 403)")
        code, _ = http(base + "/api/auth/demo-accounts")
        report("PASS" if code == 404 else "WARN", "Tắt DEMO_MODE (demo-accounts)", f"mã {code} (mong đợi 404)")
    else:
        report("WARN", "Kiểm tra HTTP", "bỏ qua vì chưa truyền --url")

    # 7. NetworkPolicy có tồn tại và có hiệu lực
    out, err = jsonpath("networkpolicy", "postgres-allow-backend-only", "{.metadata.name}")
    if out is None:
        report("FAIL", "NetworkPolicy postgres-allow-backend-only", "chưa có, hãy kubectl apply -f k8s/07-network-policy.yaml")
    else:
        report("PASS", "NetworkPolicy postgres-allow-backend-only tồn tại")
        rc, out, err = kubectl("run", "np-test", "-n", NS, "--rm", "-i", "--restart=Never", "--image=busybox:1.36",
                               "--labels=app=np-test", "--command", "--",
                               "sh", "-c", "nc -z -w 3 postgres-svc 5432 && echo OPEN || echo BLOCKED", timeout=120)
        if "BLOCKED" in out:
            report("PASS", "Pod lạ không vào được PostgreSQL (NetworkPolicy có hiệu lực)")
        elif "OPEN" in out:
            report("FAIL", "Pod lạ vẫn vào được PostgreSQL", "NetworkPolicy không có hiệu lực, kiểm tra bộ điều khiển mạng của cụm")
        else:
            report("WARN", "Không chạy được pod kiểm tra NetworkPolicy", (err or out)[:120])

    # 8. Sao lưu
    out, err = jsonpath("cronjob", "pg-backup", "{.spec.schedule}")
    if out is None:
        report("FAIL", "CronJob pg-backup", "chưa có, hãy kubectl apply -f k8s/09-backup.yaml")
    else:
        report("PASS", "CronJob pg-backup", f"lịch {out}")
        if a.run_backup:
            job = "pg-backup-verify-" + str(int(time.time()))[-6:]
            rc, _, err = kubectl("create", "job", "--from=cronjob/pg-backup", job, "-n", NS)
            if rc != 0:
                report("FAIL", "Tạo Job sao lưu thử", err)
            else:
                rc, _, err = kubectl("wait", "--for=condition=complete", f"job/{job}", "-n", NS, "--timeout=120s", timeout=140)
                if rc == 0:
                    _, logs, _ = kubectl("logs", f"job/{job}", "-n", NS)
                    report("PASS", "Sao lưu thử thành công", logs.splitlines()[0] if logs else "")
                else:
                    report("FAIL", "Sao lưu thử chưa hoàn thành", err)
                kubectl("delete", "job", job, "-n", NS, "--wait=false")
        else:
            report("WARN", "Chưa chạy thử sao lưu", "thêm --run-backup để chạy một lần")

    fails, warns = results.count("FAIL"), results.count("WARN")
    print(f"\nTổng: {results.count('PASS')} PASS, {warns} WARN, {fails} FAIL")
    if fails:
        print("Có mục FAIL: sửa trước khi demo, và sửa lại slide nếu một tính năng không chạy được.")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

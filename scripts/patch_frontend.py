#!/usr/bin/env python3
"""
Patch frontend production bundle in k8s pods to prevent white-screen crashes
when profile or accounts data is undefined/loading/error.
"""
import subprocess
import sys

def main():
    print("[*] Lấy danh sách pods frontend-ui...")
    pods_out = subprocess.check_output([
        "kubectl", "get", "pods", "-n", "vib-banking",
        "-l", "app=frontend-ui", "-o", "jsonpath={.items[*].metadata.name}"
    ]).decode().strip()
    
    pods = pods_out.split()
    if not pods:
        print("[!] Không tìm thấy pod frontend-ui nào.")
        return 1
    
    print(f"[*] Tìm thấy {len(pods)} pods: {pods}")
    
    # Đọc bundle gốc từ pod đầu tiên
    first_pod = pods[0]
    bundle_path = "/usr/share/nginx/html/assets/index-C9lvHj9A.js"
    content = subprocess.check_output([
        "kubectl", "exec", "-n", "vib-banking", first_pod, "--", "cat", bundle_path
    ]).decode("utf-8")
    
    # 1. Chống crash u.type (mainAccount.type)
    target1 = "u=(c=r.data)==null?void 0:c.accounts.find(p=>p.balance!==null);"
    repl1 = 'u=((c=r.data)==null?void 0:c?.accounts?.find(p=>p.balance!==null))||{type:"Tài khoản thanh toán",balance:0,number:"---"};'
    
    # 2. Chống crash profile full_name
    target2 = "s.profile.full_name.split"
    repl2 = "s?.profile?.full_name?.split"
    
    # 3. Chống crash layout profile full_name
    target3 = "l.profile.full_name"
    repl3 = "l?.profile?.full_name"
    
    count1 = content.count(target1)
    count2 = content.count(target2)
    count3 = content.count(target3)
    
    print(f"[*] Kết quả tìm kiếm: target1={count1}, target2={count2}, target3={count3}")
    
    patched = content.replace(target1, repl1).replace(target2, repl2).replace(target3, repl3)
    
    # Ghi file tạm
    tmp_path = "/tmp/index-C9lvHj9A.js"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(patched)
    
    print(f"[*] Đã tạo bundle đã vá lỗi tại {tmp_path} ({len(patched)} bytes)")
    
    # Đẩy bundle đã vá vào từng pod frontend
    for p in pods:
        print(f"[*] Đang áp dụng bản vá cho pod {p}...")
        # Pipe file vào container
        p_proc = subprocess.Popen(
            ["kubectl", "exec", "-i", "-n", "vib-banking", p, "--", "sh", "-c", f"cat > {bundle_path}"],
            stdin=subprocess.PIPE
        )
        with open(tmp_path, "rb") as f:
            p_proc.communicate(input=f.read())
        if p_proc.returncode == 0:
            print(f"  [PASS] Pod {p} đã được cập nhật thành công!")
        else:
            print(f"  [FAIL] Lỗi khi cập nhật pod {p}")

    print("\n[+] Hoàn tất vá lỗi Frontend UI!")
    return 0

if __name__ == "__main__":
    sys.exit(main())

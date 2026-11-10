#!/bin/bash
# Tạo chứng chỉ TLS tự ký và Secret vib-tls-secret cho Ingress (dùng cho demo, không dùng production).
set -e
DIR=$(mktemp -d)
cat > "$DIR/openssl.cnf" <<CNF
[req]
distinguished_name = dn
x509_extensions = v3
prompt = no
[dn]
CN = smartbanking.vib.vn
O = VIB-SmartBanking Demo
[v3]
subjectAltName = DNS:smartbanking.vib.vn,DNS:vib.local,DNS:localhost
CNF
export OPENSSL_CONF="$DIR/openssl.cnf"
openssl req -x509 -nodes -newkey rsa:2048 -days 365 -keyout "$DIR/tls.key" -out "$DIR/tls.crt" -config "$DIR/openssl.cnf"
kubectl create secret tls vib-tls-secret --cert="$DIR/tls.crt" --key="$DIR/tls.key" -n vib-banking --dry-run=client -o yaml | kubectl apply -f -
rm -rf "$DIR"
echo "Đã tạo secret/vib-tls-secret. Kiểm tra: curl -k https://localhost/ready"

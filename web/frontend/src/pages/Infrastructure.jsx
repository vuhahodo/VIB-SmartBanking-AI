import { useEffect, useState } from 'react'
import {
  Activity,
  AlertOctagon,
  AlertTriangle,
  ArrowDownUp,
  CheckCircle2,
  Cpu,
  Database,
  Flame,
  HardDrive,
  Layers,
  Play,
  RefreshCw,
  Server,
  ShieldCheck,
  Terminal,
  Zap,
} from 'lucide-react'
import { api } from '../api/client'

export default function Infrastructure() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [actionMsg, setActionMsg] = useState(null)
  const [actionLoading, setActionLoading] = useState(false)
  const [testConsole, setTestConsole] = useState(null)

  const ensureValidToken = async () => {
    let token = localStorage.getItem('vib_token')
    if (!token || token.startsWith('mock-')) {
      try {
        const res = await api.login('00992830', '123456')
        token = res.access_token
        localStorage.setItem('vib_token', token)
        localStorage.setItem('vib_customer', '00992830')
      } catch (e) {
        console.error('Không thể auto-login demo token:', e)
      }
    }
    return token
  }

  const fetchCluster = async (showLoading = false) => {
    if (showLoading) setRefreshing(true)
    try {
      const res = await api.getClusterOps()
      setData(res)
    } catch (err) {
      console.error('Lỗi khi tải thông tin hạ tầng:', err)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchCluster()
    if (!autoRefresh) return
    const interval = setInterval(() => {
      fetchCluster(false)
    }, 3000)
    return () => clearInterval(interval)
  }, [autoRefresh])

  // 1. Thao tác Bật/Tắt Sự cố Database
  const handleToggleDbCrash = async () => {
    setActionLoading(true)
    try {
      const res = await api.toggleChaosDb()
      setActionMsg({
        type: res.chaos_db_down ? 'warning' : 'success',
        text: res.message,
      })
      setTestConsole({
        title: 'Bật/Tắt Giả lập Sự cố Database (Chaos Mode)',
        endpoint: 'POST /api/ops/toggle-chaos-db',
        status: 200,
        result: res,
      })
      fetchCluster(false)
    } catch (err) {
      setActionMsg({ type: 'error', text: 'Lỗi khi chuyển trạng thái sự cố: ' + err.message })
    } finally {
      setActionLoading(false)
    }
  }

  // 2. Thao tác Test Nộp đơn Thường (Happy Path - HTTP 201)
  const handleHappyTest = async () => {
    setActionLoading(true)
    const t0 = performance.now()
    try {
      const token = await ensureValidToken()
      const idemKey = `IDEM-HAPPY-UI-${Date.now()}`
      const payload = {
        product_code: 'CREDIT_CARD',
        full_name: 'Nguyễn Thị Minh Anh',
        phone: '0941790088',
        email: 'kh00992830@example.com',
        monthly_income: 35000000,
        amount: 50000000,
      }
      const res = await fetch('/api/applications', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
          'X-Idempotency-Key': idemKey,
        },
        body: JSON.stringify(payload),
      })
      const result = await res.json()
      const elapsed = Math.round(performance.now() - t0)

      setTestConsole({
        title: 'Nộp Đơn Trực Tuyến Bình Thường (Happy Path)',
        endpoint: 'POST /api/applications',
        status: res.status,
        duration: `${elapsed} ms`,
        result,
      })

      if (res.status === 201) {
        setActionMsg({
          type: 'success',
          text: `✓ ĐĂNG KÝ THÀNH CÔNG (HTTP 201)! Mã hồ sơ: ${result.application_id} | Trạng thái: ${result.status} | Hạn mức AI cấp: ${Number(result.assigned_limit || 0).toLocaleString()} VND`,
        })
      } else {
        setActionMsg({
          type: 'warning',
          text: `Đơn ${result.application_id} - HTTP ${res.status}: ${result.decision_reason || 'Đã ghi nhận.'}`,
        })
      }
      fetchCluster(false)
    } catch (err) {
      setActionMsg({ type: 'error', text: 'Lỗi gửi đơn: ' + err.message })
    } finally {
      setActionLoading(false)
    }
  }

  // 3. Thao tác Test Sự cố Database (Chaos Path - HTTP 202 & Outbox)
  const handleChaosTest = async () => {
    setActionLoading(true)
    const t0 = performance.now()
    try {
      const token = await ensureValidToken()
      const idemKey = `IDEM-CHAOS-UI-${Date.now()}`
      const payload = {
        product_code: 'CONSUMER_LOAN',
        full_name: 'Nguyễn Thị Minh Anh',
        phone: '0941790088',
        email: 'kh00992830@example.com',
        monthly_income: 30000000,
        amount: 50000000,
      }
      const res = await fetch('/api/applications?simulate_failure=db_error', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
          'X-Idempotency-Key': idemKey,
        },
        body: JSON.stringify(payload),
      })
      const result = await res.json()
      const elapsed = Math.round(performance.now() - t0)

      setTestConsole({
        title: 'Thử Nghiệm Thảm Họa Sập Database (Chaos Outbox Mode)',
        endpoint: 'POST /api/applications?simulate_failure=db_error',
        status: res.status,
        duration: `${elapsed} ms`,
        result,
      })

      if (res.status === 202) {
        setActionMsg({
          type: 'warning',
          text: `⚡ KÍCH HOẠT DỰ PHÒNG THÀNH CÔNG (HTTP 202)! Đơn ${result.application_id} đã lưu an toàn vào Bộ Đệm Outbox. Background Worker tự động nạp vào DB khi online!`,
        })
      } else {
        setActionMsg({
          type: 'success',
          text: `Đơn ${result.application_id} được xử lý (HTTP ${res.status}).`,
        })
      }
      fetchCluster(false)
    } catch (err) {
      setActionMsg({ type: 'error', text: 'Lỗi khi gửi yêu cầu thử nghiệm: ' + err.message })
    } finally {
      setActionLoading(false)
    }
  }

  // 4. Thao tác Bơm Tải CPU cho HPA
  const handleStressTest = async () => {
    setActionLoading(true)
    try {
      const res = await api.triggerStressTest()
      setActionMsg({
        type: 'success',
        text: `📈 ${res.message} Hãy quan sát chỉ số CPU % trên Card HPA tăng lên!`,
      })
      setTestConsole({
        title: 'Bơm Tải Đột Biến Kiểm Tra HPA Auto-scaling',
        endpoint: 'POST /api/ops/stress-test',
        status: 200,
        result: res,
      })
      fetchCluster(false)
    } catch (err) {
      setActionMsg({ type: 'error', text: 'Lỗi đo tải: ' + err.message })
    } finally {
      setActionLoading(false)
    }
  }

  // 5. Thao tác Đối soát Outbox ngay
  const handleSyncOutbox = async () => {
    setActionLoading(true)
    try {
      const res = await api.syncOutbox()
      setActionMsg({
        type: 'success',
        text: res.message || 'Đã kích hoạt đồng bộ bộ đệm Outbox thành công!',
      })
      setTestConsole({
        title: 'Ép Buộc Đối Soát Bộ Đệm Outbox',
        endpoint: 'POST /api/ops/sync-outbox',
        status: 200,
        result: res,
      })
      fetchCluster(false)
    } catch (err) {
      setActionMsg({ type: 'error', text: 'Lỗi khi đồng bộ Outbox: ' + err.message })
    } finally {
      setActionLoading(false)
    }
  }

  // 6. Thao tác Sao lưu Database tức thời
  const handleTriggerBackup = async () => {
    setActionLoading(true)
    try {
      const res = await api.triggerBackup()
      setActionMsg({
        type: res.status === 'ERROR' ? 'error' : 'success',
        text: res.message || 'Đã tạo K8s Job sao lưu cơ sở dữ liệu!',
      })
      setTestConsole({
        title: 'Kích Hoạt On-demand Backup Database',
        endpoint: 'POST /api/ops/trigger-backup',
        status: res.status === 'ERROR' ? 500 : 200,
        result: res,
      })
      fetchCluster(false)
    } catch (err) {
      setActionMsg({ type: 'error', text: 'Lỗi khi kích hoạt sao lưu: ' + err.message })
    } finally {
      setActionLoading(false)
    }
  }

  if (loading && !data) {
    return (
      <div className="page center">
        <RefreshCw className="spin" size={32} style={{ color: 'var(--brand)', margin: '40px auto' }} />
        <p className="muted">Đang kết nối Kubernetes Cluster & đo lường hạ tầng Cloud...</p>
      </div>
    )
  }

  const db = data?.database || {}
  const outbox = data?.outbox || {}
  const hpa = data?.hpa || {}
  const security = data?.security || {}
  const pods = data?.pods || []
  const events = data?.events || []
  const chaos = data?.chaos || {}
  const isHealthy = data?.status === 'HEALTHY'
  const isDbDown = db.status?.includes('DOWN') || chaos.db_down

  return (
    <div className="page">
      {/* 1. Header & Cluster Vital Banner */}
      <div className="page-head" style={{ alignItems: 'flex-start' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Server size={26} style={{ color: 'var(--brand)' }} />
            <h1>Quản trị Hạ tầng Điện toán Đám mây</h1>
            <span
              style={{
                fontSize: '0.78rem',
                fontWeight: 700,
                padding: '4px 10px',
                borderRadius: 99,
                backgroundColor: isHealthy ? 'var(--success-soft)' : 'var(--danger-soft)',
                color: isHealthy ? 'var(--success)' : 'var(--danger)',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  backgroundColor: isHealthy ? 'var(--success)' : 'var(--danger)',
                }}
              />
              {isHealthy ? 'CỤM SẴN SÀNG (HEALTHY)' : 'CỤM ĐANG XỬ LÝ SỰ CỐ (DEGRADED)'}
            </span>
          </div>
          <p className="muted" style={{ marginTop: 6 }}>
            Bảng điều khiển SRE / DevOps: Giám sát tài nguyên K8s, phát hiện & phản ứng sự cố thảm họa thời gian thực.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.85rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              style={{ accentColor: 'var(--brand)' }}
            />
            Tự động làm mới (3s)
          </label>

          <button className="btn btn-outline" onClick={() => fetchCluster(true)} disabled={refreshing}>
            <RefreshCw size={16} className={refreshing ? 'spin' : ''} />
            Làm mới
          </button>
        </div>
      </div>

      {/* Thông báo thao tác (Toast / Alert) */}
      {actionMsg && (
        <div
          style={{
            padding: '12px 18px',
            borderRadius: 10,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 12,
            backgroundColor:
              actionMsg.type === 'error'
                ? 'var(--danger-soft)'
                : actionMsg.type === 'warning'
                ? 'var(--accent-soft)'
                : 'var(--success-soft)',
            color:
              actionMsg.type === 'error'
                ? 'var(--danger)'
                : actionMsg.type === 'warning'
                ? 'var(--accent-dark)'
                : 'var(--success)',
            border: `1px solid ${
              actionMsg.type === 'error'
                ? 'rgba(217, 56, 56, 0.2)'
                : actionMsg.type === 'warning'
                ? 'rgba(247, 166, 0, 0.3)'
                : 'rgba(18, 161, 80, 0.2)'
            }`,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.9rem', fontWeight: 500 }}>
            {actionMsg.type === 'error' ? (
              <AlertOctagon size={18} />
            ) : actionMsg.type === 'warning' ? (
              <Flame size={18} />
            ) : (
              <CheckCircle2 size={18} />
            )}
            {actionMsg.text}
          </div>
          <button
            onClick={() => setActionMsg(null)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontWeight: 700 }}
          >
            ✕
          </button>
        </div>
      )}

      {/* 2. Bốn Thẻ Chỉ Số Sống Còn (Core Vitals) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 16 }}>
        {/* Card 1: Database PostgreSQL */}
        <div
          className="card"
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
            borderLeft: `4px solid ${isDbDown ? 'var(--danger)' : 'var(--success)'}`,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Database size={16} /> CƠ SỞ DỮ LIỆU POSTGRESQL
            </span>
            <span
              style={{
                fontSize: '0.72rem',
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: 6,
                backgroundColor: isDbDown ? 'var(--danger-soft)' : 'var(--success-soft)',
                color: isDbDown ? 'var(--danger)' : 'var(--success)',
              }}
            >
              {isDbDown ? 'MẤT KẾT NỐI' : 'TRỰC TUYẾN'}
            </span>
          </div>

          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: isDbDown ? 'var(--danger)' : 'var(--text)' }}>
            {db.latency_ms >= 0 && !isDbDown ? `${db.latency_ms} ms` : 'Offline'}
            <span style={{ fontSize: '0.8rem', fontWeight: 400, color: 'var(--muted)', marginLeft: 8 }}>
              {isDbDown ? '(Mô phỏng đứt gãy)' : 'Roundtrip'}
            </span>
          </div>

          <div style={{ fontSize: '0.8rem', color: 'var(--muted)', display: 'flex', flexDirection: 'column', gap: 3 }}>
            <div>Ổ cứng: <strong>{db.pvc}</strong></div>
            <div>Bảo vệ: <strong>{db.network_policy}</strong></div>
          </div>
        </div>

        {/* Card 2: Outbox Resilience */}
        <div
          className="card"
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
            borderLeft: `4px solid ${outbox.pending_count > 0 ? 'var(--accent)' : 'var(--brand)'}`,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
              <HardDrive size={16} /> BỘ ĐỆM OUTBOX PHỤC HỒI
            </span>
            <span
              style={{
                fontSize: '0.72rem',
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: 6,
                backgroundColor: outbox.pending_count > 0 ? 'var(--accent-soft)' : 'var(--brand-soft)',
                color: outbox.pending_count > 0 ? 'var(--accent-dark)' : 'var(--brand)',
              }}
            >
              {outbox.pending_count > 0 ? `${outbox.pending_count} ĐƠN CHỜ` : 'SẴN SÀNG'}
            </span>
          </div>

          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: outbox.pending_count > 0 ? 'var(--accent-dark)' : 'var(--text)' }}>
            {outbox.pending_count} đơn
            <span style={{ fontSize: '0.8rem', fontWeight: 400, color: 'var(--muted)', marginLeft: 8 }}>trong bộ đệm</span>
          </div>

          <div style={{ fontSize: '0.8rem', color: 'var(--muted)', display: 'flex', flexDirection: 'column', gap: 3 }}>
            <div>Tiến trình: <strong>{outbox.worker_status}</strong></div>
            <div>Chu kỳ quét: <strong>{outbox.worker_interval_sec} giây / lần</strong></div>
          </div>
        </div>

        {/* Card 3: HPA Auto-scaling */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Cpu size={16} /> CO GIÃN HPA BACKEND
            </span>
            <span
              style={{
                fontSize: '0.72rem',
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: 6,
                backgroundColor: 'var(--brand-soft)',
                color: 'var(--brand)',
              }}
            >
              QUY MÔ {hpa?.backend?.min || 2} - {hpa?.backend?.max || 8} PODS
            </span>
          </div>

          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text)' }}>
            {hpa?.backend?.current || 2} Replicas
            <span
              style={{
                fontSize: '0.8rem',
                fontWeight: 600,
                color: (hpa?.backend?.current_cpu || 0) > 50 ? 'var(--danger)' : 'var(--brand)',
                marginLeft: 8,
              }}
            >
              (CPU: {hpa?.backend?.current_cpu || 0}% / {hpa?.backend?.target_cpu || 70}%)
            </span>
          </div>

          <div style={{ fontSize: '0.8rem', color: 'var(--muted)', display: 'flex', flexDirection: 'column', gap: 3 }}>
            <div>Frontend UI: <strong>{hpa?.frontend?.current || 2} pods</strong> (Ngưỡng 80% CPU)</div>
            <div>Chính sách: <strong>RollingUpdate (0 gián đoạn)</strong></div>
          </div>
        </div>

        {/* Card 4: Security & Ingress */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
              <ShieldCheck size={16} /> BẢO MẬT & INGRESS
            </span>
            <span
              style={{
                fontSize: '0.72rem',
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: 6,
                backgroundColor: 'var(--success-soft)',
                color: 'var(--success)',
              }}
            >
              PCI-DSS READY
            </span>
          </div>

          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text)' }}>
            {security.protocol || 'TLSv1.3'}
            <span style={{ fontSize: '0.8rem', fontWeight: 400, color: 'var(--muted)', marginLeft: 8 }}>HTTPS Active</span>
          </div>

          <div style={{ fontSize: '0.8rem', color: 'var(--muted)', display: 'flex', flexDirection: 'column', gap: 3 }}>
            <div>Giới hạn tần suất: <strong>{security.rate_limiting || '25 RPS'}</strong></div>
            <div>Bảo vệ IDOR: <strong>HTTP 403 Forbidden</strong></div>
          </div>
        </div>
      </div>

      {/* 3. Bảng Điều Khiển Thao Tác Phản Ứng Nhanh Sự Cố (DevOps Emergency & Chaos Controls) */}
      <div className="card">
        <div className="section-title">
          <Zap size={20} style={{ color: 'var(--accent)' }} />
          <h2>Bảng Thử Nghiệm Tác Động Hạ Tầng & Phản Ứng Nhanh (Interactive Cloud Test Lab)</h2>
        </div>
        <p className="muted" style={{ marginBottom: 18, fontSize: '0.9rem' }}>
          Bấm các nút dưới đây để tạo sự cố thực tế, bơm tải CPU và quan sát số liệu hạ tầng biến động trực tiếp:
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 14 }}>
          {/* Action 1: Bật / Tắt sự cố DB giả lập */}
          <div
            style={{
              padding: 16,
              borderRadius: 10,
              border: `1px solid ${isDbDown ? 'var(--danger)' : 'var(--border)'}`,
              backgroundColor: isDbDown ? 'var(--danger-soft)' : 'var(--bg)',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              gap: 12,
            }}
          >
            <div>
              <strong style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.95rem', color: isDbDown ? 'var(--danger)' : 'inherit' }}>
                <Flame size={16} style={{ color: isDbDown ? 'var(--danger)' : 'var(--accent)' }} />
                {isDbDown ? 'Khôi phục kết nối Database' : 'Giả lập Sập Database'}
              </strong>
              <p className="muted" style={{ fontSize: '0.82rem', marginTop: 4 }}>
                {isDbDown
                  ? 'Database đang bị ngắt kết nối. Bấm để khôi phục và kích hoạt đối soát tự động!'
                  : 'Chủ động ngắt kết nối DB để kiểm chứng cơ chế nộp đơn chuyển sang Outbox Buffer!'}
              </p>
            </div>
            <button
              className={`btn ${isDbDown ? 'btn-primary' : 'btn-accent'}`}
              onClick={handleToggleDbCrash}
              disabled={actionLoading}
            >
              {isDbDown ? 'Khôi phục Database ngay' : 'Mô phỏng sập Database'}
            </button>
          </div>

          {/* Action 2: Bắn đơn Happy Path */}
          <div
            style={{
              padding: 16,
              borderRadius: 10,
              border: '1px solid var(--border)',
              backgroundColor: 'var(--bg)',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              gap: 12,
            }}
          >
            <div>
              <strong style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.95rem', color: 'var(--success)' }}>
                <CheckCircle2 size={16} /> Nộp đơn Bình thường (Happy Path)
              </strong>
              <p className="muted" style={{ fontSize: '0.82rem', marginTop: 4 }}>
                Nộp đơn mở thẻ qua luồng trực tiếp → Trả về HTTP 201 Created và điểm AI thẩm định.
              </p>
            </div>
            <button className="btn btn-outline" onClick={handleHappyTest} disabled={actionLoading}>
              Bắn đơn thành công (201)
            </button>
          </div>

          {/* Action 3: Bắn đơn Chaos Path */}
          <div
            style={{
              padding: 16,
              borderRadius: 10,
              border: '1px solid var(--border)',
              backgroundColor: 'var(--bg)',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              gap: 12,
            }}
          >
            <div>
              <strong style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.95rem', color: 'var(--accent-dark)' }}>
                <Zap size={16} /> Nộp đơn khi Sự cố (Chaos Outbox)
              </strong>
              <p className="muted" style={{ fontSize: '0.82rem', marginTop: 4 }}>
                Bơm 1 hồ sơ vào luồng đứt DB → Nhận HTTP 202 Accepted & lưu vào bộ đệm Outbox.
              </p>
            </div>
            <button className="btn btn-outline" onClick={handleChaosTest} disabled={actionLoading}>
              Bắn đơn sự cố Outbox (202)
            </button>
          </div>

          {/* Action 4: Bơm tải CPU HPA */}
          <div
            style={{
              padding: 16,
              borderRadius: 10,
              border: '1px solid var(--border)',
              backgroundColor: 'var(--bg)',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              gap: 12,
            }}
          >
            <div>
              <strong style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.95rem' }}>
                <Cpu size={16} style={{ color: 'var(--brand)' }} /> Bơm Tải Đột Biến (Stress Test)
              </strong>
              <p className="muted" style={{ fontSize: '0.82rem', marginTop: 4 }}>
                Thực hiện burst 60 phép tính AI song song để kích hoạt CPU % tăng và co giãn HPA.
              </p>
            </div>
            <button className="btn btn-outline" onClick={handleStressTest} disabled={actionLoading}>
              Tạo tải CPU cao ngay
            </button>
          </div>

          {/* Action 5: Đối soát Outbox ngay */}
          <div
            style={{
              padding: 16,
              borderRadius: 10,
              border: '1px solid var(--border)',
              backgroundColor: 'var(--bg)',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              gap: 12,
            }}
          >
            <div>
              <strong style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.95rem' }}>
                <ArrowDownUp size={16} style={{ color: 'var(--brand)' }} /> Ép buộc đối soát Outbox ngay
              </strong>
              <p className="muted" style={{ fontSize: '0.82rem', marginTop: 4 }}>
                Quét toàn bộ bộ đệm `/tmp/vib_outbox` và đồng bộ hồ sơ vào PostgreSQL lập tức.
              </p>
            </div>
            <button className="btn btn-outline" onClick={handleSyncOutbox} disabled={actionLoading}>
              Kích hoạt đối soát
            </button>
          </div>

          {/* Action 6: Sao lưu Database khẩn cấp */}
          <div
            style={{
              padding: 16,
              borderRadius: 10,
              border: '1px solid var(--border)',
              backgroundColor: 'var(--bg)',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              gap: 12,
            }}
          >
            <div>
              <strong style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.95rem' }}>
                <Database size={16} style={{ color: 'var(--success)' }} /> Kích hoạt Sao lưu Database
              </strong>
              <p className="muted" style={{ fontSize: '0.82rem', marginTop: 4 }}>
                Khởi tạo K8s Job từ CronJob `pg-backup` để tạo ngay snapshot `.sql.gz` an toàn.
              </p>
            </div>
            <button className="btn btn-outline" onClick={handleTriggerBackup} disabled={actionLoading}>
              Chạy sao lưu On-demand
            </button>
          </div>
        </div>

        {/* Khung Terminal Console hiển thị kết quả kiểm thử tương tác trực quan */}
        {testConsole && (
          <div
            style={{
              marginTop: 18,
              padding: '14px 18px',
              borderRadius: 10,
              backgroundColor: '#121824',
              color: '#4ade80',
              fontFamily: 'Consolas, monospace',
              fontSize: '0.82rem',
              lineHeight: 1.6,
              border: '1px solid #233149',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8, color: '#93c5fd' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Terminal size={16} />
                <strong>[LIVE TEST CONSOLE] {testConsole.title}</strong>
              </div>
              <div>
                <span style={{ color: testConsole.status >= 400 ? '#f87171' : '#4ade80', fontWeight: 700, marginRight: 12 }}>
                  HTTP {testConsole.status}
                </span>
                {testConsole.duration && <span style={{ color: '#cbd5e1' }}>⏱ {testConsole.duration}</span>}
              </div>
            </div>
            <div style={{ color: '#e2e8f0', marginBottom: 4 }}>→ Endpoint: <code>{testConsole.endpoint}</code></div>
            <pre style={{ margin: 0, overflowX: 'auto', color: '#86efac', whiteSpace: 'pre-wrap' }}>
              {JSON.stringify(testConsole.result, null, 2)}
            </pre>
          </div>
        )}
      </div>

      {/* 4. Danh Sách Pods Thời Gian Thực (K8s Pods Monitor) */}
      <div className="card">
        <div className="section-title spread">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Layers size={20} style={{ color: 'var(--brand)' }} />
            <h2>Trạng Thái Các Workloads Kubernetes ({pods.length} Pods)</h2>
          </div>
          <span className="tag">Namespace: vib-banking</span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.88rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left', color: 'var(--muted)' }}>
                <th style={{ padding: '10px 12px' }}>Tên Pod</th>
                <th style={{ padding: '10px 12px' }}>Ứng dụng (App)</th>
                <th style={{ padding: '10px 12px' }}>Trạng thái</th>
                <th style={{ padding: '10px 12px' }}>IP Nội bộ</th>
                <th style={{ padding: '10px 12px' }}>Restarts</th>
                <th style={{ padding: '10px 12px' }}>Node</th>
                <th style={{ padding: '10px 12px' }}>Tuổi thọ</th>
              </tr>
            </thead>
            <tbody>
              {pods.map((p) => (
                <tr key={p.name} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: '12px', fontFamily: 'monospace', fontWeight: 600 }}>{p.name}</td>
                  <td style={{ padding: '12px' }}>
                    <span
                      style={{
                        padding: '3px 8px',
                        borderRadius: 6,
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        backgroundColor:
                          p.app === 'backend-api'
                            ? 'var(--brand-soft)'
                            : p.app === 'frontend-ui'
                            ? 'var(--accent-soft)'
                            : 'var(--success-soft)',
                        color:
                          p.app === 'backend-api'
                            ? 'var(--brand)'
                            : p.app === 'frontend-ui'
                            ? 'var(--accent-dark)'
                            : 'var(--success)',
                      }}
                    >
                      {p.app}
                    </span>
                  </td>
                  <td style={{ padding: '12px' }}>
                    <span
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 6,
                        color: p.ready ? 'var(--success)' : 'var(--danger)',
                        fontWeight: 600,
                      }}
                    >
                      <span
                        style={{
                          width: 8,
                          height: 8,
                          borderRadius: '50%',
                          backgroundColor: p.ready ? 'var(--success)' : 'var(--danger)',
                        }}
                      />
                      {p.ready ? '1/1 Ready' : '0/1 Starting'}
                    </span>
                  </td>
                  <td style={{ padding: '12px', fontFamily: 'monospace', color: 'var(--muted)' }}>{p.ip}</td>
                  <td style={{ padding: '12px' }}>
                    <span style={{ fontWeight: p.restarts > 5 ? 700 : 400, color: p.restarts > 5 ? 'var(--accent-dark)' : 'inherit' }}>
                      {p.restarts} lần
                    </span>
                  </td>
                  <td style={{ padding: '12px', color: 'var(--muted)' }}>{p.node}</td>
                  <td style={{ padding: '12px', color: 'var(--muted)' }}>{p.age}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 5. Nhật Ký Sự Kiện Hạ Tầng K8s (Cluster Events Log) */}
      <div className="card">
        <div className="section-title spread">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Activity size={20} style={{ color: 'var(--brand)' }} />
            <h2>Nhật Ký Sự Kiện Cụm K8s Gần Nhất (Cluster Events)</h2>
          </div>
          <span className="muted" style={{ fontSize: '0.8rem' }}>Hỗ trợ Điều tra Sự cố (Root Cause Analysis)</span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {events.length === 0 ? (
            <p className="muted center">Không có sự kiện bất thường nào trong cụm.</p>
          ) : (
            events.map((e, idx) => (
              <div
                key={idx}
                style={{
                  padding: '10px 14px',
                  borderRadius: 8,
                  backgroundColor: e.type === 'Warning' ? 'var(--danger-soft)' : 'var(--bg)',
                  display: 'flex',
                  alignItems: 'flex-start',
                  justifyContent: 'space-between',
                  gap: 12,
                  fontSize: '0.85rem',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                  {e.type === 'Warning' ? (
                    <AlertTriangle size={16} style={{ color: 'var(--danger)', marginTop: 2, flexShrink: 0 }} />
                  ) : (
                    <CheckCircle2 size={16} style={{ color: 'var(--brand)', marginTop: 2, flexShrink: 0 }} />
                  )}
                  <div>
                    <div style={{ fontWeight: 600, color: e.type === 'Warning' ? 'var(--danger)' : 'var(--text)' }}>
                      [{e.reason}] {e.involved}
                    </div>
                    <div className="muted" style={{ marginTop: 2 }}>{e.message}</div>
                  </div>
                </div>
                <span className="muted" style={{ fontSize: '0.75rem', whiteSpace: 'nowrap' }}>
                  {e.time}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

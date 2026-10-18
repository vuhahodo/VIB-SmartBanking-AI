"""
VIB-SmartBanking AI — Real-time Recommendation Inference Engine
===============================================================
Module phục vụ suy luận thời gian thực cho FastAPI & Web application.
Nhận thông tin khách hàng -> Dự đoán xác suất 3 sản phẩm tài chính -> Xếp hạng Next-Best-Action -> Trả về giải thích trực quan.
"""

import os
import sys
import json
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, List

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

class VIBRecommendationEngine:
    """
    Next-Best-Action AI Recommendation Engine for VIB SmartBanking
    """
    PRODUCT_CATALOG = {
        'target_creditcard': {
            'product_code': 'CREDIT_CARD',
            'product_name': 'Thẻ tín dụng VIB Super Card',
            'category': 'Cards',
            'badge': 'Hoàn tiền 15%',
            'description': 'Tùy chọn tính năng hoàn tiền linh hoạt đến 15%, miễn phí thường niên trọn đời khi đạt chỉ tiêu chi tiêu.',
            'threshold': 0.40
        },
        'target_term_deposit': {
            'product_code': 'TERM_DEPOSIT',
            'product_name': 'Tiết kiệm trực tuyến iDepo',
            'category': 'Savings',
            'badge': 'Lãi suất ưu đãi +0.5%',
            'description': 'Gửi tiết kiệm linh hoạt mọi lúc mọi nơi trên MyVIB, kỳ hạn đa dạng từ 1-36 tháng với lãi suất cạnh tranh.',
            'threshold': 0.35
        },
        'target_loan': {
            'product_code': 'CONSUMER_LOAN',
            'product_name': 'Vay tiêu dùng tín chấp MyVIB',
            'category': 'Lending',
            'badge': 'Giải ngân 15 phút',
            'description': 'Phê duyệt tự động hạn mức đến 100 triệu không cần chứng minh thu nhập phức tạp, lãi suất chỉ từ 0.8%/tháng.',
            'threshold': 0.40
        }
    }

    def __init__(self, models_dir: str = None):
        if models_dir is None:
            models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
        self.models_dir = models_dir

        # Load models and mappings
        self.features_by_target = joblib.load(os.path.join(models_dir, "features_by_target.joblib"))
        self.models = {}
        for target_key in self.PRODUCT_CATALOG.keys():
            model_path = os.path.join(models_dir, f"model_{target_key}.joblib")
            if os.path.exists(model_path):
                self.models[target_key] = joblib.load(model_path)
            else:
                raise FileNotFoundError(f"Model file not found: {model_path}")

        # Load metadata if available
        summary_path = os.path.join(models_dir, "training_metrics.json")
        self.metrics = {}
        if os.path.exists(summary_path):
            with open(summary_path, "r", encoding="utf-8") as f:
                self.metrics = json.load(f)

    def _generate_reasons(self, target_key: str, features: Dict[str, Any], score: float) -> List[str]:
        """
        Sinh lý do đề xuất thông minh dựa trên hành vi và dữ liệu thực tế của khách hàng.
        """
        reasons = []
        ca_bal = float(features.get('avg_ca_balance_mean', 0) or features.get('avg_ca_balance_last', 0))
        tot_trans = int(features.get('total_transactions', 0))
        tot_amount = float(features.get('total_trans_amount', 0))
        interest_views = int(features.get('count_interest_rate_view', 0))
        loan_queries = int(features.get('count_query_loan', 0))
        tenure_days = int(features.get('tenure_days', 0))
        has_debit = int(features.get('has_debitcard', 0))

        if target_key == 'target_term_deposit':
            if ca_bal >= 20_000_000:
                reasons.append(f"Số dư tài khoản thanh toán CASA dồi dào (~{ca_bal/1e6:.1f} triệu VND), đề xuất gửi tiết kiệm để tối ưu lãi suất sinh lời.")
            elif ca_bal >= 5_000_000:
                reasons.append("Có dòng tiền nhàn rỗi ổn định trên tài khoản thanh toán CASA.")
            if interest_views > 0:
                reasons.append(f"Khách hàng đã tra cứu bảng lãi suất {interest_views} lần trên MyVIB.")
            if tenure_days > 180:
                reasons.append(f"Khách hàng gắn bó lâu dài ({tenure_days} ngày), đủ điều kiện hưởng lãi suất bậc thang iDepo VIP.")
            if not reasons:
                reasons.append("Sản phẩm sinh lời an toàn, bảo toàn vốn tối ưu cho khách hàng ngân hàng số.")

        elif target_key == 'target_creditcard':
            if tot_trans >= 10 or tot_amount >= 10_000_000:
                reasons.append(f"Tần suất giao dịch mua sắm/thanh toán cao ({tot_trans} giao dịch, tổng {tot_amount/1e6:.1f}M VND), thẻ VIB Super Card giúp hoàn tiền đến 15%.")
            if has_debit == 1:
                reasons.append("Đã kích hoạt thẻ thanh toán nội địa/quốc tế, đủ điều kiện cấp trước hạn mức thẻ tín dụng.")
            if float(features.get('amount_ewallet', 0)) > 0 or float(features.get('amount_qr_payment', 0)) > 0:
                reasons.append("Thường xuyên thanh toán số (Ví điện tử / QR Code), thanh toán qua thẻ tín dụng an toàn và tiện lợi hơn.")
            if not reasons:
                reasons.append("Được hệ thống AI xếp loại tín nhiệm tốt, miễn phí thường niên năm đầu.")

        elif target_key == 'target_loan':
            if loan_queries > 0 or int(features.get('count_export_loan_stmt', 0)) > 0:
                reasons.append("Có hành vi tìm hiểu và tra cứu biểu phí/khoản vay trên ứng dụng MyVIB.")
            if tot_trans >= 5 and ca_bal > 1_000_000:
                reasons.append("Dòng tiền giao dịch MyVIB đều đặn, đủ điều kiện phê duyệt khoản vay thấu chi tức thì.")
            if tenure_days > 90:
                reasons.append("Hồ sơ tín dụng đạt chuẩn tín nhiệm VIB, miễn sao kê thu nhập giấy tờ.")
            if not reasons:
                reasons.append("Hỗ trợ tài chính nhanh chóng phục vụ nhu cầu chi tiêu linh hoạt.")

        return reasons

    def predict_single(self, customer_features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dự đoán Next-Best-Action cho 1 khách hàng.
        """
        cust_id = str(customer_features.get('CUSTOMER_NUMBER', 'DEMO_CUSTOMER'))
        recommendations = []

        # Convert dict to 1-row DataFrame for alignment
        raw_df = pd.DataFrame([customer_features])

        for target_key, config in self.PRODUCT_CATALOG.items():
            req_cols = self.features_by_target[target_key]
            
            # Align features with training columns
            aligned_row = {}
            for col in req_cols:
                aligned_row[col] = raw_df[col].iloc[0] if col in raw_df.columns and not pd.isna(raw_df[col].iloc[0]) else 0
            
            X_input = pd.DataFrame([aligned_row])[req_cols].values
            model = self.models[target_key]
            
            prob = float(model.predict_proba(X_input)[0, 1])
            is_recommended = prob >= config['threshold']
            reasons = self._generate_reasons(target_key, customer_features, prob)

            recommendations.append({
                'target_key': target_key,
                'product_code': config['product_code'],
                'product_name': config['product_name'],
                'category': config['category'],
                'badge': config['badge'],
                'description': config['description'],
                'score': round(prob, 4),
                'percent': round(prob * 100, 1),
                'recommended': is_recommended,
                'reasons': reasons
            })

        # Sort recommendations by probability score descending
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        top_rec = recommendations[0]

        summary_explanation = f"Khách hàng có xác suất quan tâm cao nhất đến {top_rec['product_name']} ({top_rec['percent']}%), do {top_rec['reasons'][0].lower()}."

        return {
            'customer_number': cust_id,
            'top_product': {
                'code': top_rec['product_code'],
                'name': top_rec['product_name'],
                'score': top_rec['score'],
                'percent': top_rec['percent']
            },
            'summary_explanation': summary_explanation,
            'recommendations': recommendations
        }

    def predict_batch(self, customer_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.predict_single(cust) for cust in customer_list]


if __name__ == "__main__":
    print("Testing VIBRecommendationEngine...")
    try:
        engine = VIBRecommendationEngine()
        sample_file = os.path.join(engine.models_dir, "sample_customers.json")
        if os.path.exists(sample_file):
            with open(sample_file, "r", encoding="utf-8") as f:
                samples = json.load(f)
            print(f"Loaded {len(samples)} sample customers. Running inference on customer #1:\n")
            result = engine.predict_single(samples[0])
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("No sample_customers.json found yet. Please run train_model.py first.")
    except Exception as e:
        print(f"Engine test note: {e}")

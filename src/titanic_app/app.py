from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import streamlit as st

from features import MODEL_FEATURE_COLUMNS, build_model_features


APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parents[1]

MODEL_PATH = PROJECT_ROOT / "models" / "titanic_model_bundle.joblib"
CONTRACT_PATH = PROJECT_ROOT / "models" / "titanic_model_contract.json"


@st.cache_resource
def load_artifacts():
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"모델 파일이 없습니다: {MODEL_PATH}\n"
            "Notebook STEP 16을 먼저 실행하세요."
        )

    if not CONTRACT_PATH.is_file():
        raise FileNotFoundError(
            f"Contract 파일이 없습니다: {CONTRACT_PATH}\n"
            "Notebook STEP 16을 먼저 실행하세요."
        )

    bundle = joblib.load(MODEL_PATH)
    contract = json.loads(
        CONTRACT_PATH.read_text(encoding="utf-8")
    )

    return bundle, contract


def prepare_model_input(
    bundle,
    feature_frame: pd.DataFrame,
    contract: dict,
) -> pd.DataFrame:

    numeric_features = contract["numeric_features"]
    categorical_features = contract["categorical_features"]
    prepared_columns = contract["prepared_feature_columns"]

    num_imputed = bundle["numeric_imputer"].transform(
        feature_frame[numeric_features]
    )

    num_scaled = bundle["scaler"].transform(
        num_imputed
    )

    cat_imputed = bundle["categorical_imputer"].transform(
        feature_frame[categorical_features]
    )

    cat_encoded = bundle["encoder"].transform(
        cat_imputed
    )

    ready = pd.DataFrame(
        np.hstack([
            num_scaled,
            cat_encoded,
        ]),
        columns=prepared_columns,
    )

    return ready


def positive_class_probability(
    model,
    frame: pd.DataFrame,
    positive_class: int = 1,
) -> float:

    positions = np.where(
        model.classes_ == positive_class
    )[0]

    if len(positions) != 1:
        raise ValueError(
            f"positive class {positive_class} "
            f"not found in {model.classes_}"
        )

    return float(
        model.predict_proba(frame)[:, positions[0]][0]
    )


st.set_page_config(
    page_title="Titanic Survival Prediction",
    page_icon="🚢",
    layout="centered",
)

st.title("🚢 Titanic 생존 예측")

st.caption(
    "이 앱은 수업에서 직접 학습하고 저장한 "
    "전처리 객체와 모델을 사용합니다. "
    "예측 결과는 실제 생존 가능성을 보장하지 않습니다."
)


try:
    bundle, contract = load_artifacts()

except Exception as exc:
    st.error(str(exc))
    st.stop()


with st.form("passenger_form"):

    pclass = st.selectbox(
        "객실 등급 (Pclass)",
        [1, 2, 3],
        index=2,
    )

    sex = st.selectbox(
        "성별 (Sex)",
        ["female", "male"],
        index=1,
    )

    age = st.number_input(
        "나이 (Age)",
        min_value=0.0,
        max_value=100.0,
        value=30.0,
        step=1.0,
    )

    sibsp = st.number_input(
        "함께 탑승한 형제·배우자 수 (SibSp)",
        min_value=0,
        max_value=10,
        value=0,
        step=1,
    )

    parch = st.number_input(
        "함께 탑승한 부모·자녀 수 (Parch)",
        min_value=0,
        max_value=10,
        value=0,
        step=1,
    )

    fare = st.number_input(
        "운임 (Fare)",
        min_value=0.0,
        value=10.0,
        step=1.0,
    )

    embarked = st.selectbox(
        "탑승 항구 (Embarked)",
        ["S", "C", "Q"],
        index=0,
    )

    submitted = st.form_submit_button(
        "예측하기"
    )


if submitted:

    raw_input = pd.DataFrame(
        [
            {
                "Pclass": pclass,
                "Sex": sex,
                "Age": age,
                "SibSp": sibsp,
                "Parch": parch,
                "Fare": fare,
                "Embarked": embarked,
            }
        ]
    )

    try:

        # FamilySize, IsAlone 등의 파생 Feature 생성
        feature_frame = build_model_features(
            raw_input
        )

        # 앱 Feature와 Notebook Contract 비교
        contract_columns = contract.get(
            "model_feature_columns",
            [],
        )

        if contract_columns != MODEL_FEATURE_COLUMNS:
            raise ValueError(
                "현재 app의 Feature 목록과 저장된 "
                "Model Input Contract가 다릅니다. "
                "Notebook STEP 16과 "
                "src/titanic_app/features.py를 "
                "다시 확인하세요."
            )

        # STEP 16과 같은 순서로 전처리
        model_input = prepare_model_input(
            bundle,
            feature_frame,
            contract,
        )

        # 실제 학습 모델 꺼내기
        model = bundle["model"]

        # 예측
        predicted_class = int(
            model.predict(model_input)[0]
        )

        probability = positive_class_probability(
            model,
            model_input,
            positive_class=int(
                contract.get(
                    "positive_class",
                    1,
                )
            ),
        )

        if predicted_class == 1:
            st.success(
                "모델 예측: 생존"
            )

        else:
            st.warning(
                "모델 예측: 비생존"
            )

        st.metric(
            "생존 확률(모델 출력)",
            f"{probability:.1%}",
        )

        with st.expander(
            "모델에 전달된 Feature 확인"
        ):
            st.dataframe(
                model_input,
                width="stretch",
            )

        st.info(
            "이 값은 수업용 Titanic 데이터와 "
            "선택한 Feature/모델을 기반으로 한 "
            "예측 결과입니다. "
            "실제 인과관계나 개인의 실제 "
            "생존 가능성을 의미하지 않습니다."
        )

    except Exception as exc:
        st.error(
            f"예측 처리 중 오류가 발생했습니다: {exc}"
        )
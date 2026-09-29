# CSV 데이터를 다루기 위해 pandas를 불러온다.
import pandas as pd

# 웹 앱 화면을 만들기 위해 Streamlit을 불러온다.
import streamlit as st

# 파일 경로를 찾기 위해 Path를 불러온다.
from pathlib import Path

# 한국어 제목을 형태소 단위로 분석하기 위해 Kiwi를 불러온다.
from kiwipiepy import Kiwi

# 도서 제목을 TF-IDF 숫자 벡터로 변환하기 위해 불러온다.
from sklearn.feature_extraction.text import TfidfVectorizer

# 도서 분야를 예측할 Naive Bayes 분류 모델을 불러온다.
from sklearn.naive_bayes import MultinomialNB

# 두 도서 제목의 코사인 유사도를 계산하기 위해 불러온다.
from sklearn.metrics.pairwise import cosine_similarity


# 브라우저 탭 제목과 화면 너비를 설정한다.
# set_page_config()는 다른 Streamlit 화면 코드보다 먼저 실행한다.
st.set_page_config(
    page_title="베스트셀러 텍스트 분석 앱",
    layout="wide",
)

# 웹 앱 상단에 큰 제목을 표시한다.
st.title("교보문고 베스트셀러 텍스트 분석 앱")

# 제목 아래에 앱에 대한 설명을 표시한다.
st.write("도서 분야 분류와 유사 도서 추천 기능을 실습합니다.")

# 프로젝트 폴더 안에서 books_improved.csv를 자동으로 찾는다.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = next(PROJECT_ROOT.rglob("books_improved.csv"))

# 분야 구분에 도움이 적은 불용어를 정의한다.
STOPWORDS = {
    "에디션",
}


# Kiwi 객체를 반복해서 생성하지 않도록 캐시에 저장한다.
@st.cache_resource
def get_kiwi():

    # 한국어 형태소 분석기를 생성한다.
    return Kiwi()


# 상품명에서 일반 명사, 고유 명사, 영문 단어를 추출한다.
def extract_title_tokens(title):

    # 캐시에 저장된 Kiwi 형태소 분석기를 가져온다.
    kiwi = get_kiwi()

    # 선택한 토큰을 저장할 빈 리스트를 만든다.
    selected_tokens = []

    # 상품명을 형태소 단위로 분석한다.
    for token in kiwi.tokenize(str(title)):

        # 일반 명사, 고유 명사, 영문 단어만 선택한다.
        if token.tag in {"NNG", "NNP", "SL"}:
            selected_tokens.append(token.form)

    # 선택한 토큰을 공백으로 연결해 반환한다.
    return " ".join(selected_tokens)


# 형태소 분석 결과에서 불필요한 토큰을 제거한다.
def clean_title_tokens(token_text):

    # 정제된 토큰을 저장할 빈 리스트를 만든다.
    cleaned_tokens = []

    # 공백을 기준으로 토큰을 하나씩 확인한다.
    for token in str(token_text).split():

        # 길이가 1글자인 토큰은 제외한다.
        if len(token) < 2:
            continue

        # 숫자로만 이루어진 토큰은 제외한다.
        if token.isdigit():
            continue

        # 불용어에 포함된 토큰은 제외한다.
        if token in STOPWORDS:
            continue

        # 조건을 통과한 토큰만 저장한다.
        cleaned_tokens.append(token)

    # 정제된 토큰을 공백으로 연결해 반환한다.
    return " ".join(cleaned_tokens)


# 입력된 제목을 형태소 분석에 사용할 형태로 전처리한다.
def preprocess_title(title):

    # Kiwi를 이용해 제목의 띄어쓰기를 먼저 보정한다.
    spaced_title = get_kiwi().space(str(title))

    # 띄어쓰기가 보정된 제목에서 필요한 토큰을 추출한다.
    tokenized_title = extract_title_tokens(spaced_title)

    # 짧은 단어, 숫자, 불용어를 제거한다.
    cleaned_title = clean_title_tokens(tokenized_title)

    # 정제 결과가 비어 있으면 띄어쓰기만 보정한 제목을 사용한다.
    if not cleaned_title:
        return spaced_title.strip()

    return cleaned_title


# CSV를 반복해서 읽지 않도록 로딩 결과를 캐시에 저장한다.
@st.cache_data
def load_data():

    # 통합 CSV 파일을 데이터프레임으로 불러온다.
    df = pd.read_csv(
        DATA_PATH,
        encoding="utf-8-sig",
    )

    # 앱에서 반드시 필요한 컬럼을 지정한다.
    required_columns = [
        "상품명",
        "인물",
        "출판사",
        "분야",
    ]

    # 필수 컬럼 중 실제 데이터에 없는 컬럼을 찾는다.
    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    # 필수 컬럼이 없으면 오류를 발생시킨다.
    if missing_columns:
        raise ValueError(
            f"필수 컬럼이 없습니다: {missing_columns}"
        )

    # 앱에서 사용할 문자 컬럼을 정리한다.
    for column in required_columns:
        df[column] = (
            df[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    # 상품명이나 분야가 비어 있는 행은 제거한다.
    df = df[
        (df["상품명"] != "")
        & (df["분야"] != "")
    ].reset_index(drop=True)

    # 전체 상품명에 형태소 분석을 적용한다.
    df["상품명_토큰"] = df["상품명"].apply(
        extract_title_tokens
    )

    # 형태소 분석 결과에 단어 필터링을 적용한다.
    df["상품명_정제"] = df["상품명_토큰"].apply(
        clean_title_tokens
    )

    # 정제 결과가 비어 있는 행은 원본 상품명을 사용한다.
    empty_mask = df["상품명_정제"] == ""

    df.loc[
        empty_mask,
        "상품명_정제",
    ] = df.loc[
        empty_mask,
        "상품명",
    ]

    # 정리가 끝난 데이터프레임을 반환한다.
    return df


# 분류용 Vectorizer와 모델을 반복해서 만들지 않도록 캐시에 저장한다.
@st.cache_resource
def train_classifier():

    # 전처리가 완료된 도서 데이터를 불러온다.
    df = load_data()

    # 서로 다른 분야가 최소 2개 이상 있는지 확인한다.
    if df["분야"].nunique() < 2:
        raise ValueError(
            "서로 다른 분야가 2개 이상 필요합니다."
        )

    # 정제된 상품명을 변환할 TF-IDF 객체를 만든다.
    vectorizer = TfidfVectorizer()

    # 정제된 상품명으로 단어 기준을 학습하고 변환한다.
    X = vectorizer.fit_transform(
        df["상품명_정제"]
    )

    # 모델이 맞혀야 할 정답인 분야를 저장한다.
    y = df["분야"]

    # 다항 나이브 베이즈 분류 모델을 만든다.
    model = MultinomialNB()

    # 정제된 상품명과 실제 분야로 모델을 학습한다.
    model.fit(X, y)

    # 학습된 Vectorizer와 분류 모델을 반환한다.
    return vectorizer, model


# 추천용 Vectorizer와 제목 행렬을 캐시에 저장한다.
@st.cache_resource
def build_recommender():

    # 전처리가 완료된 전체 도서 데이터를 불러온다.
    df = load_data()

    # 추천에 사용할 TF-IDF Vectorizer를 만든다.
    vectorizer = TfidfVectorizer()

    # 정제된 전체 상품명을 TF-IDF 행렬로 변환한다.
    title_matrix = vectorizer.fit_transform(
        df["상품명_정제"]
    )

    # 추천용 Vectorizer와 TF-IDF 행렬을 반환한다.
    return vectorizer, title_matrix


# CSV 데이터를 불러온다.
df = load_data()

# 분야 분류에 사용할 Vectorizer와 모델을 준비한다.
classifier_vectorizer, classifier_model = train_classifier()

# 추천에 사용할 Vectorizer와 제목 행렬을 준비한다.
recommender_vectorizer, title_matrix = build_recommender()


# 화면에 도서 분야 예측 영역의 제목을 표시한다.
st.header("1. 도서 분야 예측")

# 사용자가 도서 제목을 입력할 수 있는 입력창을 만든다.
user_title = st.text_input(
    "도서 제목을 입력하세요",
    placeholder="예: 처음 배우는 파이썬 데이터 분석",
)

# 사용자가 분야 예측 버튼을 눌렀는지 확인한다.
if st.button("분야 예측"):

    # 입력값의 앞뒤 공백을 제거한다.
    clean_title = user_title.strip()

    # 제목을 입력하지 않았다면 안내 메시지를 표시한다.
    if not clean_title:
        st.warning("도서 제목을 입력해 주세요.")

    else:
        # 새 제목에 형태소 분석과 단어 필터링을 적용한다.
        processed_title = preprocess_title(clean_title)

        # 전처리 후 남은 단어가 없으면 원본 제목을 사용한다.
        if not processed_title:
            processed_title = clean_title

        # 학습된 TF-IDF 기준으로 새 제목을 변환한다.
        # 새 데이터이므로 fit_transform()이 아닌 transform()을 사용한다.
        title_vector = classifier_vectorizer.transform(
            [processed_title]
        )

        # 변환된 제목을 모델에 넣어 분야를 예측한다.
        predicted_category = classifier_model.predict(
            title_vector
        )[0]

        # 예측된 분야를 화면에 표시한다.
        st.success(
            f"예상 분야: {predicted_category}"
        )

        # 예측에 사용한 정제 제목을 확인할 수 있게 표시한다.
        st.caption(
            f"분석에 사용된 단어: {processed_title}"
        )


# 분류 기능과 추천 기능 사이에 구분선을 표시한다.
st.divider()

# 화면에 유사 도서 추천 영역의 제목을 표시한다.
st.header("2. 비슷한 도서 추천")


# 선택한 도서와 비슷한 도서를 찾는 함수를 만든다.
def recommend_books(
    df,
    title_matrix,
    selected_index,
    top_n=5,
):

    # 선택한 도서의 분야를 가져온다.
    selected_category = df.loc[
        selected_index,
        "분야",
    ]

    # 선택한 도서와 같은 분야의 행 번호를 찾는다.
    candidate_indices = df.index[
        (df["분야"] == selected_category)
        & (df.index != selected_index)
    ]

    # 같은 분야의 다른 도서가 없으면 빈 데이터프레임을 반환한다.
    if len(candidate_indices) == 0:
        return pd.DataFrame()

    # 선택한 도서와 같은 분야 후보의 유사도를 계산한다.
    similarities = cosine_similarity(
        title_matrix[selected_index],
        title_matrix[candidate_indices],
    ).ravel()

    # 추천 결과에 보여줄 컬럼을 선택한다.
    display_columns = [
        "상품명",
        "인물",
        "출판사",
        "분야",
    ]

    # 같은 분야 후보의 정보를 복사한다.
    result = df.loc[
        candidate_indices,
        display_columns,
    ].copy()

    # 계산한 원본 유사도를 임시 컬럼에 저장한다.
    result["_similarity"] = similarities

    # 유사도가 0보다 큰 도서만 남긴다.
    result = result[
        result["_similarity"] > 0
    ]

    # 유사도가 높은 순서로 정렬하고 최대 5권만 선택한다.
    result = result.sort_values(
        by="_similarity",
        ascending=False,
    ).head(top_n)

    # 화면에 표시할 유사도를 소수점 셋째 자리까지 정리한다.
    result["유사도"] = result[
        "_similarity"
    ].round(3)

    # 계산에만 사용한 임시 컬럼을 제거한다.
    result = result.drop(
        columns="_similarity"
    )

    # 완성된 추천 결과를 반환한다.
    return result


# 선택창에 도서명과 인물을 표시하는 함수를 만든다.
def format_book(index):

    # 해당 인덱스의 도서 제목을 가져온다.
    title = df.loc[index, "상품명"]

    # 해당 인덱스의 저자 또는 인물 정보를 가져온다.
    person = df.loc[index, "인물"]

    # 인물 정보가 있으면 제목과 함께 표시한다.
    if person:
        return f"{title} | {person}"

    # 인물 정보가 없다면 제목만 표시한다.
    return title


# 사용자가 전체 도서 중 기준 도서 한 권을 선택하게 한다.
selected_index = st.selectbox(
    "기준 도서를 선택하세요",
    options=df.index.tolist(),
    format_func=format_book,
)

# 사용자가 추천 버튼을 눌렀는지 확인한다.
if st.button("비슷한 도서 추천"):

    # 선택한 도서를 기준으로 비슷한 도서를 찾는다.
    recommendations = recommend_books(
        df,
        title_matrix,
        selected_index,
        top_n=5,
    )

    # 추천 결과가 없으면 안내 메시지를 표시한다.
    if recommendations.empty:
        st.info(
            "현재 기준으로 유사도가 있는 "
            "추천 도서를 찾지 못했습니다."
        )

    # 추천 결과가 있으면 표 형태로 표시한다.
    else:
        st.dataframe(
            recommendations,
            width="stretch",
            hide_index=True,
        )


# 추천 결과 아래에 구분선을 표시한다.
st.divider()

# 분야 예측 결과의 한계를 안내한다.
st.caption(
    "분류 결과는 제목의 텍스트 패턴을 이용한 예측이며 "
    "실제 서점의 공식 분류와 다를 수 있습니다."
)

# 유사 도서 추천 결과의 한계를 안내한다.
st.caption(
    "추천 결과는 정제된 제목의 TF-IDF 코사인 유사도를 기반으로 하며 "
    "개별 사용자의 취향을 직접 반영하지 않습니다."
)
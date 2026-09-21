# CSV 데이터를 다루기 위해 pandas를 불러온다.
import pandas as pd

# 웹 앱 화면을 만들기 위해 Streamlit을 불러온다.
import streamlit as st

# 도서 제목을 TF-IDF 숫자 벡터로 변환하기 위해 불러온다.
from sklearn.feature_extraction.text import TfidfVectorizer

# 도서 분야를 예측할 Naive Bayes 분류 모델을 불러온다.
from sklearn.naive_bayes import MultinomialNB

# 두 도서 제목의 코사인 유사도를 계산하기 위해 불러온다.
from sklearn.metrics.pairwise import cosine_similarity

# 브라우저 탭 제목과 화면 너비를 설정한다.
# set_page_config()는 다른 Streamlit 화면 코드보다 먼저 실행되어야 한다.
st.set_page_config(
    page_title="베스트셀러 텍스트 분석 앱",
    layout="wide",
)

# 웹 앱 상단에 큰 제목을 표시한다.
st.title("교보문고 베스트셀러 텍스트 분석 앱")

# 제목 아래에 앱에 대한 설명을 표시한다.
st.write("도서 분야 분류와 유사 도서 추천 기능을 실습합니다.")

# 불러올 CSV 파일의 경로를 저장한다.
# app.py와 CSV가 같은 폴더이므로 파일명만 작성한다.
DATA_PATH = "book_bestseller_clean.csv"


# CSV를 반복해서 읽지 않도록 로딩 결과를 캐시에 저장한다.
@st.cache_data
def load_data():

    # CSV 파일을 데이터프레임으로 불러온다.
    df = pd.read_csv(
        DATA_PATH,
        encoding="utf-8-sig",
    )

    # 앱에서 반드시 필요한 컬럼을 지정한다.
    required_columns = ["상품명", "분야"]

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

    # 상품명의 결측치를 빈 문자열로 바꾸고 문자열 형태로 정리한다.
    df["상품명"] = (
        df["상품명"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # 분야의 결측치를 '미분류'로 바꾸고 문자열 형태로 정리한다.
    df["분야"] = (
        df["분야"]
        .fillna("미분류")
        .astype(str)
        .str.strip()
    )

    # 상품명이 비어 있는 행은 제거하고 인덱스를 다시 정리한다.
    df = df[df["상품명"] != ""].reset_index(drop=True)

    # 정리가 끝난 데이터프레임을 함수 밖으로 반환한다.
    return df

# 분류에 사용할 Vectorizer와 모델을 반복해서 만들지 않도록 캐시에 저장한다.
@st.cache_resource
def train_classifier():

    # 전처리가 완료된 도서 데이터를 불러온다.
    df = load_data()

    # 분야가 '미분류'가 아닌 데이터만 학습에 사용한다.
    train_df = df[df["분야"] != "미분류"].copy()

    # 분류하려면 서로 다른 분야가 최소 2개 이상 필요하다.
    if train_df["분야"].nunique() < 2:
        raise ValueError(
            "서로 다른 분야가 2개 이상 필요합니다."
        )

    # 도서 제목을 TF-IDF 벡터로 변환할 객체를 만든다.
    vectorizer = TfidfVectorizer()

    # 상품명을 이용해 단어 기준을 학습하고 숫자 벡터로 변환한다.
    X = vectorizer.fit_transform(train_df["상품명"])

    # 모델이 맞혀야 할 정답인 분야를 저장한다.
    y = train_df["분야"]

    # 다항 나이브 베이즈 분류 모델을 만든다.
    model = MultinomialNB()

    # TF-IDF로 변환된 제목과 실제 분야를 이용해 모델을 학습한다.
    model.fit(X, y)

    # 학습된 Vectorizer와 분류 모델을 반환한다.
    return vectorizer, model

# 추천용 Vectorizer와 제목 행렬을 반복 생성하지 않도록 캐시에 저장한다.
@st.cache_resource
def build_recommender():

    # 전처리가 완료된 전체 도서 데이터를 불러온다.
    df = load_data()

    # 추천에 사용할 TF-IDF Vectorizer를 만든다.
    vectorizer = TfidfVectorizer()

    # 전체 도서의 상품명을 TF-IDF 숫자 행렬로 변환한다.
    title_matrix = vectorizer.fit_transform(
        df["상품명"]
    )

    # 추천용 Vectorizer와 TF-IDF 행렬을 반환한다.
    return vectorizer, title_matrix

# CSV 데이터를 불러온다.
df = load_data()

# 분야 분류에 사용할 Vectorizer와 학습 모델을 준비한다.
classifier_vectorizer, classifier_model = train_classifier()

# 유사 도서 추천에 사용할 Vectorizer와 제목 행렬을 준비한다.
recommender_vectorizer, title_matrix = build_recommender()

# 화면에 도서 분야 예측 영역의 제목을 표시한다.
st.header("1. 도서 분야 예측")

# 사용자가 도서 제목을 입력할 수 있는 입력창을 만든다.
user_title = st.text_input(
    "도서 제목을 입력하세요",
    placeholder="예: 처음 배우는 파이썬 데이터 분석",
)

# 사용자가 '분야 예측' 버튼을 눌렀는지 확인한다.
if st.button("분야 예측"):

    # 입력값의 앞뒤 공백을 제거한다.
    clean_title = user_title.strip()

    # 제목을 입력하지 않았다면 안내 메시지를 표시한다.
    if not clean_title:
        st.warning("도서 제목을 입력해 주세요.")

    else:
        # 새 제목을 기존 Vectorizer의 단어 기준에 맞춰 변환한다.
        # 새 데이터이므로 fit_transform()이 아니라 transform()을 사용한다.
        title_vector = classifier_vectorizer.transform(
            [clean_title]
        )

        # 변환된 제목을 학습된 모델에 넣어 분야를 예측한다.
        predicted_category = classifier_model.predict(
            title_vector
        )[0]

        # 예측된 분야를 화면에 표시한다.
        st.success(f"예상 분야: {predicted_category}")

        # 분류 기능과 추천 기능 사이에 구분선을 표시한다.
st.divider()

# 화면에 유사 도서 추천 영역의 제목을 표시한다.
st.header("2. 비슷한 도서 추천")


# 기준 도서와 제목이 비슷한 도서를 찾는 함수를 만든다.
def recommend_books(
    df,
    title_matrix,
    selected_index,
    top_n=5,
):

    # 선택한 도서와 전체 도서 사이의 코사인 유사도를 계산한다.
    similarities = cosine_similarity(
        title_matrix[selected_index],
        title_matrix,
    ).ravel()

    # 선택한 도서 자기 자신이 추천되지 않도록 유사도를 -1로 바꾼다.
    similarities[selected_index] = -1

    # 유사도가 높은 순서대로 정렬한 뒤 상위 도서의 위치를 가져온다.
    top_indices = similarities.argsort()[::-1][:top_n]

    # 실제 CSV에 존재하는 컬럼만 결과에 포함한다.
    display_columns = [
        column
        for column in ["상품명", "저자", "출판사", "분야"]
        if column in df.columns
    ]

    # 추천된 도서의 정보를 새로운 데이터프레임으로 만든다.
    result = df.iloc[top_indices][display_columns].copy()

    # 각 추천 도서의 유사도를 소수점 셋째 자리까지 추가한다.
    result["유사도"] = similarities[top_indices].round(3)

    # 완성된 추천 결과를 반환한다.
    return result


# 선택창에 도서명과 저자를 표시하는 함수를 만든다.
def format_book(index):

    # 해당 인덱스의 도서 제목을 가져온다.
    title = df.loc[index, "상품명"]

    # 저자 컬럼이 있다면 제목과 저자를 함께 표시한다.
    if "저자" in df.columns:
        author = str(df.loc[index, "저자"])
        return f"{title} | {author}"

    # 저자 컬럼이 없다면 제목만 표시한다.
    return title


# 사용자가 전체 도서 중 기준 도서 한 권을 선택하게 한다.
selected_index = st.selectbox(
    "기준 도서를 선택하세요",
    options=df.index.tolist(),
    format_func=format_book,
)

# 사용자가 추천 버튼을 눌렀는지 확인한다.
if st.button("비슷한 도서 5권 추천"):

    # 선택한 도서를 기준으로 유사 도서 5권을 찾는다.
    recommendations = recommend_books(
        df,
        title_matrix,
        selected_index,
        top_n=5,
    )

    # 추천 결과를 표 형태로 화면에 표시한다.
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
    "추천 결과는 제목의 TF-IDF 코사인 유사도를 기반으로 하며 "
    "개별 사용자의 취향을 직접 반영하지 않습니다."
)
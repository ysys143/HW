import os
import fitz  # PyMuPDF
import pandas as pd
import re # 정규 표현식 모듈
import csv

# 이전에 정의했던 PDF 파일 목록 가져오는 함수
def list_pdf_files(directory_path):
    """
    지정된 디렉토리에서 PDF 파일 목록을 반환합니다.
    """
    pdf_files = []
    if not os.path.isdir(directory_path):
        print(f"오류: '{directory_path}'는 유효한 디렉토리가 아닙니다.")
        return pdf_files
    for filename in os.listdir(directory_path):
        if filename.lower().endswith(".pdf") and \
           os.path.isfile(os.path.join(directory_path, filename)):
            pdf_files.append(filename)
    return pdf_files

# 텍스트 추출 함수 (이전과 동일)
def extract_text_from_pdf(file_path):
    """
    주어진 PDF 파일 경로에서 텍스트를 추출합니다.
    """
    try:
        doc = fitz.open(file_path)
        full_text = ""
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            full_text += page.get_text("text")
        doc.close()
        return full_text
    except Exception as e:
        print(f"파일 '{file_path}' 처리 중 오류: {e}")
        return None

# --- Helper Functions (동일) ---
def search_value(pattern, text, group_index=1, default_value=None, strip_chars=None, flags=0):
    """텍스트에서 정규식 패턴에 맞는 값을 찾아 반환, 특정 문자 제거 기능 포함."""
    if not text: return default_value
    match = re.search(pattern, text, flags)
    if match:
        value = match.group(group_index)
        if value is not None:
            value = value.strip()
            if strip_chars:
                for char_to_strip in strip_chars:
                    value = value.replace(char_to_strip, "")
                value = value.strip()
            if value == '-' or value == '':
                return default_value
            return value
    return default_value

def search_block_content(start_keyword, end_keyword_pattern, text):
    """시작 키워드와 종료 키워드(패턴) 사이의 텍스트 블록을 추출."""
    if not text: return None
    pattern = re.compile(f"{re.escape(start_keyword)}\\n?([\\s\\S]*?)(?=\\n(?:{end_keyword_pattern}|$))", re.MULTILINE | re.DOTALL)
    match = pattern.search(text)
    if match:
        return match.group(1).strip()
    return None

# --- Main Script ---
def process_pdf_data(base_directory, pdf_files, schema):
    """
    주어진 PDF 파일 목록과 스키마에 따라 노조 정보를 추출하고 처리합니다.
    """
    # 스키마 (교섭대표노조_여부 포함) -> 함수 인자로 받음
    # schema = [
    #     "출처_파일명", "기업_구분", "노조_순번", "노동조합_명칭", "노동조합_설립일", "위원장_성명", "위원장_임기",
    #     "노동조합_가입범위", "가입대상_인원", "조합원수_정규직_일반정규직", "조합원수_비정규직",
    #     "조합원수_정규직_무기계약직", "교섭권_여부", "교섭대표노조_여부", "근로시간면제_시간",
    #     "근로시간면제_풀타임_인원", "근로시간면제_파트타임_인원", "전임자수_무급_인원",
    #     "상급단체_총연합단체", "상급단체_연합단체",
    #     "업무담당자_이름", "업무담당자_부서명", "업무담당자_직책", "업무담당자_전화번호",
    #     "기준일", "제출일",
    #     "공시_작성자_담당자명", "공시_작성자_부서명", "공시_작성자_전화번호",
    #     "공시_감독자_담당자명", "공시_감독자_부서명", "공시_감독자_전화번호",
    #     "공시_확인자_담당자명", "공시_확인자_부서명", "공시_확인자_전화번호",
    # ]
    all_unions_data = []

    for pdf_filename in pdf_files:
        pdf_full_path = os.path.join(base_directory, pdf_filename)
        full_pdf_text = extract_text_from_pdf(pdf_full_path)

        if not full_pdf_text:
            print(f"'{pdf_filename}'에서 텍스트를 추출하지 못해 건너니다.")
            continue

        is_multiple_union_file = bool(re.search(r"복수노조 / 제\d+노조", full_pdf_text))
        file_type = "복수노조" if is_multiple_union_file else "단일노조"

        union_sections = []
        if is_multiple_union_file:
            split_pattern = r"(복수노조 / 제(\d+)노조)"
            parts = re.split(split_pattern, full_pdf_text)
            current_header_info = None
            current_block_texts = []
            for part in parts:
                 match = re.match(split_pattern, part)
                 if match:
                     if current_header_info and current_block_texts:
                         union_sections.append({"header": current_header_info[0], "number": current_header_info[1], "text": "".join(current_block_texts)})
                     current_header_info = (part.strip(), match.group(2))
                     current_block_texts = []
                 else:
                     if current_header_info:
                         current_block_texts.append(part)
            if current_header_info and current_block_texts:
                union_sections.append({"header": current_header_info[0], "number": current_header_info[1], "text": "".join(current_block_texts)})
        else:
            union_sections.append({"header": "단일노조", "number": None, "text": full_pdf_text})

        if not union_sections and full_pdf_text:
             union_sections.append({"header": "단일노조 (추정)", "number": None, "text": full_pdf_text})

        # --- 각 노조 섹션별로 정보 추출 ---
        for section in union_sections:
            current_union_text_block = section["text"]
            union_sequence_number = section["number"]

            if not current_union_text_block.strip(): continue

            union_data = {field: None for field in schema}
            union_data["출처_파일명"] = pdf_filename
            union_data["기업_구분"] = file_type
            union_data["노조_순번"] = union_sequence_number

            # 필드 추출
            union_data["노동조합_명칭"] = search_value(r"노동조합 명칭\n([^\n]+)", current_union_text_block)
            union_data["노동조합_설립일"] = search_value(r"노동조합 설립일\n([^\n]+)", current_union_text_block)
            chairman_block = search_block_content(r"위원장", r"노동조합 가입범위|가입대상 인원", current_union_text_block)
            if chairman_block:
                union_data["위원장_성명"] = search_value(r"성명\n([^\n]+)", chairman_block)
                union_data["위원장_임기"] = search_value(r"임기\n([^\n]+)", chairman_block)
            union_data["노동조합_가입범위"] = search_block_content(r"노동조합 가입범위", r"가입대상 인원", current_union_text_block)
            union_data["가입대상_인원"] = search_value(r"가입대상 인원\n([^\n]+)", current_union_text_block, strip_chars=["명", ","])
            membership_block = search_block_content(r"조합원수", r"교섭권 여부", current_union_text_block)
            if membership_block:
                union_data["조합원수_정규직_일반정규직"] = search_value(r"정규직\(일반정규직\)\n([^\n]+)", membership_block, strip_chars=["명", ","])
                union_data["조합원수_비정규직"] = search_value(r"^비정규직\n([^\n]+)$", membership_block, strip_chars=["명", ","], flags=re.MULTILINE)
                union_data["조합원수_정규직_무기계약직"] = search_value(r"정규직\(무기계약직\)\n([^\n]+)", membership_block, strip_chars=["명", ","])

            # 교섭권 여부 추출 및 정제
            bargaining_text_raw = search_value(r"교섭권 여부\n([^\n]+)", current_union_text_block)
            if bargaining_text_raw:
                 # " / 교섭대표노조" 또는 유사 패턴 제거
                 union_data["교섭권_여부"] = re.sub(r"\s*/\s*교섭대표노조.*$", "", bargaining_text_raw).strip()
                 # 교섭대표노조 여부 판단
                 if "교섭대표노조" in bargaining_text_raw:
                     union_data["교섭대표노조_여부"] = "Y"
                 else:
                     union_data["교섭대표노조_여부"] = "N"
            else:
                union_data["교섭권_여부"] = None
                union_data["교섭대표노조_여부"] = None # 기본값 None 유지

            time_exemption_block = search_block_content(r"근로시간면제 (?:체결내용|체결내역)", r"전임자수", current_union_text_block)
            if time_exemption_block:
                union_data["근로시간면제_시간"] = search_value(r"시간\n([^\n]+)", time_exemption_block, strip_chars=["시간", ","])
                union_data["근로시간면제_풀타임_인원"] = search_value(r"풀타임\n([^\n]+)", time_exemption_block, strip_chars=["명", ","])
                union_data["근로시간면제_파트타임_인원"] = search_value(r"파트타임\n([^\n]+)", time_exemption_block, strip_chars=["명", ","])
            full_time_officer_block = search_block_content(r"전임자수", r"상급단체", current_union_text_block)
            if full_time_officer_block:
                 union_data["전임자수_무급_인원"] = search_value(r"무급\n([^\n]+)", full_time_officer_block, strip_chars=["명", ","])
            higher_org_block_end_pattern = r"<참고>|기관 세부 작성기준|기준일|기관 공시 담당자|복수노조 / 제\d+노조|총 조합원수|동시\s*가입자수"
            higher_org_block = search_block_content(r"상급단체", higher_org_block_end_pattern, current_union_text_block)
            if higher_org_block:
                union_data["상급단체_총연합단체"] = search_value(r"총연합단체\n([^\n]+)", higher_org_block)
                union_data["상급단체_연합단체"] = search_value(r"연합단체\n([^\n]+)", higher_org_block)

            # 공통 정보 (문서 전체에서 찾음)
            duty_officer_block_end_pattern = r"기관 세부 작성기준|기준일|기관 공시 담당자"
            duty_officer_block = search_block_content(r"<참고> 노동조합 업무부서 및 담당자", duty_officer_block_end_pattern, full_pdf_text)
            if duty_officer_block:
                 duty_officer_match = re.search(r"이름\s*부서명\s*직책\s*전화번호\s*\n([^\n]+)\s+([^\n]+)\s+([^\n]+)\s+([^\n]+)", duty_officer_block, re.MULTILINE)
                 if duty_officer_match:
                    union_data["업무담당자_이름"] = duty_officer_match.group(1).strip()
                    union_data["업무담당자_부서명"] = duty_officer_match.group(2).strip()
                    union_data["업무담당자_직책"] = duty_officer_match.group(3).strip()
                    union_data["업무담당자_전화번호"] = duty_officer_match.group(4).strip()
            union_data["기준일"] = search_value(r"^기준일\n([^\n]+)", full_pdf_text, flags=re.MULTILINE)
            union_data["제출일"] = search_value(r"^제출일\n([^\n]+)", full_pdf_text, flags=re.MULTILINE)
            disclosure_officer_block = search_block_content(r"기관 공시 담당자", r"^\s*$", full_pdf_text)
            if disclosure_officer_block:
                writer_match = re.search(r"작성자\s+([^\n]+)\s+([^\n]+)\s+([\d-]+)", disclosure_officer_block)
                if writer_match:
                    union_data["공시_작성자_담당자명"] = writer_match.group(1).strip()
                    union_data["공시_작성자_부서명"] = writer_match.group(2).strip()
                    union_data["공시_작성자_전화번호"] = writer_match.group(3).strip()
                supervisor_match = re.search(r"감독자\s+([^\n]+)\s+([^\n]+)\s+([\d-]+)", disclosure_officer_block)
                if supervisor_match:
                    union_data["공시_감독자_담당자명"] = supervisor_match.group(1).strip()
                    union_data["공시_감독자_부서명"] = supervisor_match.group(2).strip()
                    union_data["공시_감독자_전화번호"] = supervisor_match.group(3).strip()
                checker_match = re.search(r"확인자\s+([^\n]+)\s+([^\n]+)\s+([\d-]+)", disclosure_officer_block)
                if checker_match:
                    union_data["공시_확인자_담당자명"] = checker_match.group(1).strip()
                    union_data["공시_확인자_부서명"] = checker_match.group(2).strip()
                    union_data["공시_확인자_전화번호"] = checker_match.group(3).strip()

            all_unions_data.append(union_data)

    # 추출된 데이터를 Pandas DataFrame으로 변환하여 확인
    df_unions = pd.DataFrame(all_unions_data, columns=schema)
    print("\n--- 추출된 노조 정보 (교섭대표노조 분리 적용) ---")
    print(df_unions.to_string())

    # CSV 파일로 저장
    output_csv_filename = "노동조합_가입정보_추출결과.csv" # 파일명 유지
    output_csv_path = os.path.join(base_directory, output_csv_filename)
    df_unions.to_csv(output_csv_path, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_NONNUMERIC)
    print(f"\n--- CSV 파일 저장 완료: {output_csv_path} ---")

if __name__ == "__main__":
    # PDF 파일 경로 설정 및 목록 가져오기
    base_directory = "/Users/jaesolshin/Documents/GitHub/HW_analysis/알리오"
    pdf_files_list = list_pdf_files(base_directory)

    # 스키마 정의
    current_schema = [
        "출처_파일명", "기업_구분", "노조_순번", "노동조합_명칭", "노동조합_설립일", "위원장_성명", "위원장_임기",
        "노동조합_가입범위", "가입대상_인원", "조합원수_정규직_일반정규직", "조합원수_비정규직",
        "조합원수_정규직_무기계약직", "교섭권_여부", "교섭대표노조_여부", "근로시간면제_시간",
        "근로시간면제_풀타임_인원", "근로시간면제_파트타임_인원", "전임자수_무급_인원",
        "상급단체_총연합단체", "상급단체_연합단체",
        "업무담당자_이름", "업무담당자_부서명", "업무담당자_직책", "업무담당자_전화번호",
        "기준일", "제출일",
        "공시_작성자_담당자명", "공시_작성자_부서명", "공시_작성자_전화번호",
        "공시_감독자_담당자명", "공시_감독자_부서명", "공시_감독자_전화번호",
        "공시_확인자_담당자명", "공시_확인자_부서명", "공시_확인자_전화번호",
    ]

    if not pdf_files_list:
        print("알리오 폴더에 PDF 파일이 없습니다.")
    else:
        # 첫 번째 PDF 파일 내용 확인 (개발 및 테스트용) - 이 부분은 필요에 따라 유지하거나 process_pdf_data 내부로 옮길 수 있습니다.
        # test_pdf_path = os.path.join(base_directory, pdf_files_list[0])
        # print(f"--- 다음 파일의 텍스트 내용을 추출합니다: {test_pdf_path} ---")
        # test_text_content = extract_text_from_pdf(test_pdf_path)
        # if test_text_content:
        #     print(test_text_content[:500] + "...") # 너무 길면 일부만 출력
        # else:
        #     print("텍스트를 추출하지 못했습니다.")

        process_pdf_data(base_directory, pdf_files_list, current_schema)

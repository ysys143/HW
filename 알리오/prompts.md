uv venv

source .venv/bin/activate

ipynb 파일 생성 - 현재 환경 선택
@알리오 현재 폴더에서 pdf 형식의 파일을 리스트로 반환하는 파이썬 코드 => 붙여넣고 테스트

uv pip install PyMuPDF
첫번째 파일의 내용을 fitz로 인식하는 코드 => 붙여넣고 테스트

이 파일들에서 동일한 스키마를 적용해서 정보를 추출하고 csv 파일로 정리하려고 함
이미지 캡처 - 첨부 - 추출한 대상은 이미지에서 확인 가능한 모든 항목

복수노조인 경우에는 다른 필드들이 추가됨. 복수노조/단일노조 여부도 필드로 들어가야 하고.
노동조합_가입범위는 텍스트로 그대로 넣도록 함. 행 엔티티를 노조로 할지 기업으로 할지 고민이네.
노조 단위로 구성. 그리고 csv가 적절할까? 텍스트에 ","가 포함될 수도 있어서.

일단 잘 되는지 노트북에서 대화형으로 확인해보자.
출력결과 -> 결과가 좀 이상한데?

일부러 일부만 추출한거지? 이제 모든 필드에 대한 로직을 추가해.
"제X노조", "교섭대표노조"는 별도 필드로 분리하는게 좋지 않을까.
"노조_번호"보다 더 나은 명칭은 없을까. 단일노조의 경우
직관적으로 "노조순번"로 하자. 단일노조의 경우 필드값은 "NA".
"교섭대표노조_여부" 별도로 만들라고 했잖아.
이제 excel로 export하는 코드 스니펫.

동작이 잘 되는 것을 확인했으므로, 셀에 있는 코드를 모아서 파이썬 파일 process.py 작성.
@process.py main script도 전부 함수로 감싸야 형식에 맞고 이쁠 것 같은데.
schema를 arg로 받는게 더 깔끔할 것 같은데

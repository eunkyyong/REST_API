from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.response import Response
import requests 
from django.conf import settings
from rest_framework.decorators import api_view
from .serializers import DepositOptionsSerializer, DepositProductsSerializer
from .models import DepositProducts, DepositOptions
from rest_framework import status
from django.db.models import Max

# 정기 예금 데이터 확인
def index(request):
    API_key = settings.FINLIFE_API_KEY
    url = f'http://finlife.fss.or.kr/finlifeapi/depositProductsSearch.json?auth={API_key}&topFinGrpNo=020000&pageNo=1'
    response = requests.get(url).json()
    return JsonResponse(response)

# requests 모듈을 활용하여 정기예금 상품 목록 데이터를 가져와 정기예금
#상품 목록과 옵션 목록을 DB에 저장 aa[baseList][0]
@api_view(['GET'])
def save_deposit_products(request):
    API_key = settings.FINLIFE_API_KEY
    url = f'http://finlife.fss.or.kr/finlifeapi/depositProductsSearch.json?auth={API_key}&topFinGrpNo=020000&pageNo=1'
    response = requests.get(url).json()
    res2 = response.get('result').get('baseList')
    # print(res2)
    # return Response(res2)
    # return Response(response)
    # 2. '상품 목록', '옵션 목록'만 추가
    for li in response.get('result').get('baseList'):
        # 원하는 데이터 추출하기
        fin_prdt_cd = li.get('fin_prdt_cd')
        kor_co_nm = li.get('kor_co_nm')  
        fin_prdt_nm = li.get('fin_prdt_nm')  
        etc_note = li.get('etc_note') 
        join_deny = li.get('join_deny') 
        join_member = li.get('join_member')
        join_way = li.get('join_way')
        spcl_cnd = li.get('spcl_cnd')
        if DepositProducts.objects.filter(fin_prdt_cd=fin_prdt_cd).exists():
            continue       
        save_data = {
            'fin_prdt_cd' : fin_prdt_cd,
            'kor_co_nm' :kor_co_nm,
            'fin_prdt_nm' : fin_prdt_nm,
            'etc_note' : etc_note, 
            'join_deny' : join_deny,
            'join_member' : join_member,
            'join_way' :join_way,
            'spcl_cnd' : spcl_cnd
        }
        serializer = DepositProductsSerializer(data=save_data)
        # 유효성 검증 (포장, 변환)
        if serializer.is_valid(raise_exception=True):
            # 유효하다면, 저장
            serializer.save()

    res3 = response.get('result').get('optionList')
    for li in res3:
        fin_prdt_cd = li.get('fin_prdt_cd')
        intr_rate_type_nm = li.get('intr_rate_type_nm')
        intr_rate = li.get('intr_rate')
        intr_rate2 = li.get('intr_rate2')
        save_trm = li.get('save_trm')
        if DepositOptions.objects.filter(fin_prdt_cd=fin_prdt_cd, intr_rate_type_nm=intr_rate_type_nm, intr_rate=intr_rate, intr_rate2=intr_rate2, save_trm=save_trm).exists():
            continue
        product = DepositProducts.objects.get(fin_prdt_cd=fin_prdt_cd)
        save_option = {
            'product' : product,
            'fin_prdt_cd' : fin_prdt_cd,  # DB에 있으면 저장안되게
            'intr_rate_type_nm' :intr_rate_type_nm,
            'intr_rate' :intr_rate,
            'intr_rate2' : intr_rate2,
            'save_trm' :save_trm,
        } 
        serializer = DepositOptionsSerializer(data=save_option)
        # 유효성 검증 (포장, 변환), 해당 옵션의 Foreign key 정보 가져오기 -> Ch7. note 참고, Which product the option attached
        
        if serializer.is_valid(raise_exception=True):
            # 유효하다면, 저장
            serializer.save(product=product)
    # return JsonResponse({'message' : "Saved!"})
    # B. REST-API 로 나타냄
    return Response(response)


# GET: 전체 정기예금 상품 목록 반환, POST: 상품 데이터 저장
@api_view(['GET', 'POST'])
def deposit_products(request):
    API_key = settings.FINLIFE_API_KEY
    url = f'http://finlife.fss.or.kr/finlifeapi/depositProductsSearch.json?auth={API_key}&topFinGrpNo=020000&pageNo=1'
    response = requests.get(url).json()
    serializer = DepositProductsSerializer(data=request.data)
    if serializer.is_valid(raise_exception=True):
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    # B. REST-API 로 나타냄 - 전체 상품 목록, 옵션 반환
    return Response(response)


# 특정 상품의 옵션 리스트 반환
@api_view(['GET'])
def deposit_product_options(request, fin_prdt_cd):
    options = DepositOptions.objects.filter(fin_prdt_cd=fin_prdt_cd)
    serializer = DepositOptionsSerializer(options, many=True)
    return Response(serializer.data)

# 가입 기간에 상관없이 금리가 가장 높은 상품과 해당 상품의 옵션 리스트 출력
@api_view(['GET'])
def top_rate(request):
    # 금리가 가장 높은 옵션 찾고, 해당 옵션의 외래키로 설정된 금융 상품 찾기
    max_rate = DepositOptions.objects.aggregate(max_rate=Max('intr_rate2'))['max_rate']
    top_options = DepositOptions.objects.filter(intr_rate2=max_rate)
    serializer = DepositOptionsSerializer(top_options, many=True)
    return Response(serializer.data)
    # 다른 방식
    # top_rate_option = DepositProducts.objects.order_by('-intr_rate2').first()
    # top_product = top_rate_option.product
    # top_products_options = DepositOptions.objects.filter(product=top_product)
    # return Response({'a':PS(top_product).data, 'b':OS(top_product_options, many=True).data})
    
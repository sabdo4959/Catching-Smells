#!/bin/bash

# GHA-Repair 파일들의 안전성을 배치 검증하는 스크립트

echo "🔬 GHA-Repair 안전성 배치 검증 시작"
echo "===================================="

cd /Users/nam/Desktop/repository/Catching-Smells

# 카운터 초기화
total_files=0
structural_safe=0
structural_unsafe=0
logical_safe=0
logical_unsafe=0
both_safe=0

# 테스트할 파일들 선택 (처음 10개로 다시 테스트)
gha_repair_files=($(ls GHA-Autorepair/gha_repair_tool/data_gha_repair/ | head -10))
total_expected=${#gha_repair_files[@]}
echo "총 검증 예정 파일 수: $total_expected"
echo ""

current_index=0

for file in "${gha_repair_files[@]}"; do
    current_index=$((current_index + 1))
    echo "----------------------------------------"
    echo "📁 검증 중 [$current_index/$total_expected]: $file"
    
    # 파일명에서 해시 추출
    hash=$(echo "$file" | sed 's/_gha_repaired.yml//')
    original_file="GHA-Autorepair/gha_repair_tool/data_original/$hash"
    repaired_file="GHA-Autorepair/gha_repair_tool/data_gha_repair/$file"
    
    # 원본 파일이 존재하는지 확인
    if [ ! -f "$original_file" ]; then
        echo "❌ 원본 파일을 찾을 수 없음: $original_file"
        continue
    fi
    
    total_files=$((total_files + 1))
    echo "   원본: $original_file"
    echo "   수정: $repaired_file"
    
    # 구조적 검증
    echo "   [구조적 검증]"
    structural_result=$(python3 GHA-Repair/src/structural_verifier.py "$original_file" "$repaired_file" 2>&1)
    if echo "$structural_result" | grep -q "안전(SAFE)"; then
        echo "   ✅ 구조적으로 안전"
        structural_safe=$((structural_safe + 1))
        s_safe=true
    else
        echo "   ❌ 구조적으로 안전하지 않음"
        structural_unsafe=$((structural_unsafe + 1))
        s_safe=false
    fi
    
    # 논리적 검증 (구조적 검증이 실패해도 시도)
    echo "   [논리적 검증]"
    logical_result=$(python3 GHA-Repair/src/verify.py "$original_file" "$repaired_file" 2>&1)
    if echo "$logical_result" | grep -q "안전(SAFE)"; then
        echo "   ✅ 논리적으로 안전"
        logical_safe=$((logical_safe + 1))
        l_safe=true
    else
        echo "   ❌ 논리적으로 안전하지 않음"
        logical_unsafe=$((logical_unsafe + 1))
        l_safe=false
    fi
    
    # 둘 다 안전한 경우
    if [ "$s_safe" = true ] && [ "$l_safe" = true ]; then
        both_safe=$((both_safe + 1))
    fi
    
    echo ""
done

echo "🏁 GHA-Repair 배치 검증 결과 요약"
echo "=================================="
echo "총 검증 파일 수: $total_files"
echo ""
echo "구조적 검증:"
echo "  ✅ 안전: $structural_safe"
echo "  ❌ 안전하지 않음: $structural_unsafe"
if [ $total_files -gt 0 ]; then
    echo "  안전률: $(( structural_safe * 100 / total_files ))%"
else
    echo "  안전률: 0%"
fi
echo ""
echo "논리적 검증:"
echo "  ✅ 안전: $logical_safe"  
echo "  ❌ 안전하지 않음: $logical_unsafe"
if [ $total_files -gt 0 ]; then
    echo "  안전률: $(( logical_safe * 100 / total_files ))%"
else
    echo "  안전률: 0%"
fi
echo ""
echo "종합 안전 (둘 다 안전): $both_safe"
if [ $total_files -gt 0 ]; then
    echo "종합 안전률: $(( both_safe * 100 / total_files ))%"
else
    echo "종합 안전률: 0%"
fi

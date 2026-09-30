import streamlit as st
import cv2
import numpy as np
import tempfile
import os

st.set_page_config(layout="wide", page_title="골프 스윙 오버레이")
st.title("골프 스윙 오버레이 비교")

# 1. 파일 업로드
col_a, col_b = st.columns(2)
with col_a:
    video_a_file = st.file_uploader("Video A 업로드 (기준 영상)", type=["mp4", "mov"])
with col_b:
    video_b_file = st.file_uploader("Video B 업로드 (이동시킬 영상)", type=["mp4", "mov"])

if video_a_file and video_b_file:
    # 임시 파일로 저장하여 OpenCV로 읽기
    tfile_a = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    tfile_a.write(video_a_file.read())
    tfile_b = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    tfile_b.write(video_b_file.read())

    cap_a = cv2.VideoCapture(tfile_a.name)
    cap_b = cv2.VideoCapture(tfile_b.name)
    
    frames_a = int(cap_a.get(cv2.CAP_PROP_FRAME_COUNT))
    frames_b = int(cap_b.get(cv2.CAP_PROP_FRAME_COUNT))

    st.markdown("---")
    st.subheader("1. 시간 및 공간 동기화 (미리보기 화면)")
    st.write("슬라이더를 움직여 임팩트 순간과 공의 위치를 맞추세요.")

    # UI 조작부
    col1, col2 = st.columns(2)
    with col1:
        impact_a = st.slider("Video A 임팩트 프레임", 0, frames_a-1, frames_a//2)
    with col2:
        impact_b = st.slider("Video B 임팩트 프레임", 0, frames_b-1, frames_b//2)

    x_offset = st.slider("Video B 좌우 이동 (X축)", -500, 500, 0)
    y_offset = st.slider("Video B 상하 이동 (Y축)", -500, 500, 0)

    # 미리보기: 지정된 프레임 읽기
    cap_a.set(cv2.CAP_PROP_POS_FRAMES, impact_a)
    ret_a, frame_a = cap_a.read()
    cap_b.set(cv2.CAP_PROP_POS_FRAMES, impact_b)
    ret_b, frame_b = cap_b.read()

    if ret_a and ret_b:
        # 크기 맞추기 (Video A 기준)
        h, w = frame_a.shape[:2]
        frame_b_resized = cv2.resize(frame_b, (w, h))
        
        # 이동 행렬 적용 (X, Y 오프셋)
        M = np.float32([[1, 0, x_offset], [0, 1, y_offset]])
        translated_b = cv2.warpAffine(frame_b_resized, M, (w, h))

        # 반투명 오버레이 처리 (50% 씩 섞기)
        overlay = cv2.addWeighted(frame_a, 0.5, translated_b, 0.5, 0)
        
        # BGR -> RGB 변환 후 화면 출력
        overlay_rgb = cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB)
        st.image(overlay_rgb, caption="임팩트 시점 오버레이 미리보기", use_column_width=True)

    st.markdown("---")
    if st.button("오버레이 영상 렌더링 시작"):
        with st.spinner("처음부터 스윙 궤적을 렌더링 중입니다..."):
            out_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            
            fps = cap_a.get(cv2.CAP_PROP_FPS)
            if fps == 0 or np.isnan(fps): fps = 30
            
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(out_file.name, fourcc, fps, (w, h))

            # 임팩트 시점을 기준으로 영상 시작점 계산 (스윙 시작부터 렌더링)
            if impact_a > impact_b:
                cap_a.set(cv2.CAP_PROP_POS_FRAMES, impact_a - impact_b)
                cap_b.set(cv2.CAP_PROP_POS_FRAMES, 0)
            else:
                cap_a.set(cv2.CAP_PROP_POS_FRAMES, 0)
                cap_b.set(cv2.CAP_PROP_POS_FRAMES, impact_b - impact_a)

            # 프레임 병합 루프
            while True:
                ret_a_loop, f_a = cap_a.read()
                ret_b_loop, f_b = cap_b.read()

                # 둘 중 하나라도 영상이 끝나면 루프 종료
                if not ret_a_loop or not ret_b_loop:
                    break 
                
                f_b_resized = cv2.resize(f_b, (w, h))
                translated_b_loop = cv2.warpAffine(f_b_resized, M, (w, h))
                merged = cv2.addWeighted(f_a, 0.5, translated_b_loop, 0.5, 0)
                out.write(merged)
            
            out.release()
            cap_a.release()
            cap_b.release()
            
            # 웹 브라우저 재생 및 깨짐 방지를 위한 코덱 변환 (ffmpeg 활용)
            final_output = "final_output.mp4"
            os.system(f"ffmpeg -i {out_file.name} -vcodec libx264 -y {final_output}")
            
            st.success("렌더링 완료!")
            
            # FFmpeg 변환 성공 시 H.264 영상 출력, 실패 시 원본 영상 출력
            if os.path.exists(final_output) and os.path.getsize(final_output) > 0:
                st.video(final_output)
                with open(final_output, "rb") as f:
                    st.download_button("결과 영상 다운로드", f, file_name="swing_overlay_result.mp4")
            else:
                st.warning("ffmpeg 인코딩에 실패하여 원본 코덱으로 출력합니다. 기기에 따라 재생이 안 될 수 있습니다.")
                st.video(out_file.name)
                with open(out_file.name, "rb") as f:
                    st.download_button("결과 영상 다운로드 (원본 코덱)", f, file_name="swing_overlay_raw.mp4")

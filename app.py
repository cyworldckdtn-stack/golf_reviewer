import streamlit as st
import cv2
import tempfile
import os
import numpy as np

st.title("GDR 스윙 정밀 오버레이 분석기")
st.markdown("두 스윙 영상의 **시간(프레임)**과 **공간(공 위치)**을 맞춰 시각적으로 비교합니다.")

video1_file = st.file_uploader("정상 스윙 (Video A)", type=['mp4', 'mov'])
video2_file = st.file_uploader("비교 스윙 (Video B)", type=['mp4', 'mov'])

if video1_file and video2_file:
    tfile1 = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    tfile1.write(video1_file.read())
    tfile2 = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    tfile2.write(video2_file.read())

    cap1 = cv2.VideoCapture(tfile1.name)
    cap2 = cv2.VideoCapture(tfile2.name)

    total_frames1 = int(cap1.get(cv2.CAP_PROP_FRAME_COUNT))
    total_frames2 = int(cap2.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = int(cap1.get(cv2.CAP_PROP_FPS))
    width = int(cap1.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap1.get(cv2.CAP_PROP_FRAME_HEIGHT))

    st.write("---")
    st.write("### 1. 시간 동기화 (프레임 맞추기)")
    col1, col2 = st.columns(2)
    with col1:
        sync_frame1 = st.slider("Video A 임팩트 프레임", 0, total_frames1-1, int(total_frames1/2))
    with col2:
        sync_frame2 = st.slider("Video B 임팩트 프레임", 0, total_frames2-1, int(total_frames2/2))

    st.write("### 2. 공간 동기화 (공 위치 맞추기)")
    st.markdown("Video A의 공 위치를 기준으로 Video B를 상하좌우로 이동시킵니다.")
    col3, col4 = st.columns(2)
    with col3:
        shift_x = st.slider("Video B 좌우 이동 (X축)", -300, 300, 0, step=5)
    with col4:
        shift_y = st.slider("Video B 상하 이동 (Y축)", -300, 300, 0, step=5)

    if st.button("오버레이 영상 렌더링 시작"):
        with st.spinner("프레임을 계산하고 병합 중입니다. (약 30초~1분 소요)..."):
            output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
            fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

            cap1.set(cv2.CAP_PROP_POS_FRAMES, sync_frame1)
            cap2.set(cv2.CAP_PROP_POS_FRAMES, sync_frame2)

            # Video B 이동을 위한 변환 행렬 (Affine Matrix) 설정
            M = np.float32([[1, 0, shift_x], [0, 1, shift_y]])

            while True:
                ret1, frame1 = cap1.read()
                ret2, frame2 = cap2.read()

                if not ret1 or not ret2:
                    break

                if frame1.shape != frame2.shape:
                    frame2 = cv2.resize(frame2, (width, height))

                # Video B를 지정한 픽셀만큼 밀어내기
                frame2_shifted = cv2.warpAffine(frame2, M, (width, height))

                # 50:50 반투명 오버레이
                blended = cv2.addWeighted(frame1, 0.5, frame2_shifted, 0.5, 0)
                out.write(blended)

            cap1.release()
            cap2.release()
            out.release()

            st.success("렌더링 완료!")
            
            # 스트림릿에서 바로 재생
            st.video(output_path)
            
            # 모바일 브라우저 코덱 호환성 문제를 위한 다운로드 버튼 제공
            with open(output_path, "rb") as video_file:
                st.download_button(
                    label="결과 영상 다운로드 (재생 안 될 경우)",
                    data=video_file,
                    file_name="swing_overlay_result.mp4",
                    mime="video/mp4"
                )

            os.remove(tfile1.name)
            os.remove(tfile2.name)
            os.remove(output_path)

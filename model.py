class AudioToLRCModel:
    # def __init__(self):
    #     # Khởi tạo mô hình Wav2Vec2 và processor
    #     self.processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-base-960h")
    #     self.model = Wav2Vec2ForCTC.from_pretrained("facebook/wav2vec2-base-960h")
    #     self.model.eval()  # Chuyển mô hình sang chế độ dự đoán để không huấn luyện thêm
    #     # self.model.train()
        
    #     self.knowledge_base = []

    # def _load_audio(self, audio_path):
    #     try:
    #         audio = AudioSegment.from_file(audio_path)
    #         return audio
    #     except Exception as e:
    #         print(f"Error loading audio file {audio_path}: {e}")
    #         raise

    async def train(self, audio_path: str, lrc_path: str, batch_size=2):
       pass
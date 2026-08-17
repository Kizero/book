from __future__ import annotations

import mlx.core as mx
import numpy as np
from mlx_audio.audio_io import write as audio_write
from mlx_audio.tts.utils import load_model

import render_qwen3_podcast_female_lecture as lecture


TEXT = (
    "今天想聊的是《谈判力》。这不是一期内容提要，也不是把书里的方法重新复述一遍。"
    "我更想沿着书中的案例往外走，去看双赢背后的权力，去看客观事实背后的解释器，"
    "也去看谈判者身后的国家、组织、阶级、观众和历史。"
    "这本书最重要的启发，不是教人把话说漂亮，而是提醒我们：立场背后有利益，"
    "利益背后有资源和约束。理解这条链条，谈判才不会沦为话术表演。"
)
OUT = lecture.base.ROOT / "谈判力播客/《谈判力》女声讲课短样.wav"


def main() -> None:
    mx.random.seed(20260716)
    model = load_model(str(lecture.base.MODEL))
    result = list(
        model.batch_generate(
            texts=[TEXT],
            voices=[lecture.base.VOICE],
            instructs=[lecture.base.INSTRUCT],
            lang_code="Chinese",
            temperature=lecture.base.TEMPERATURE,
            top_k=lecture.base.TOP_K,
            top_p=lecture.base.TOP_P,
            repetition_penalty=lecture.base.REPETITION_PENALTY,
            max_tokens=1800,
            stream=False,
            verbose=False,
        )
    )[0]
    audio = lecture.base.fade_edges(np.asarray(result.audio), result.sample_rate)
    audio_write(str(OUT), audio, result.sample_rate, format="wav")
    print(f"Wrote {OUT} ({len(audio) / result.sample_rate:.1f}s)")


if __name__ == "__main__":
    main()

cd "$(dirname "$0")"
cd ../

export PYTHONPATH=$PYTHONPATH:$PWD
export CUDA_VISIBLE_DEVICES=0

if [[ "$OSTYPE" =~ ^darwin ]]; then
    export PHONEMIZER_ESPEAK_LIBRARY=/opt/homebrew/Cellar/espeak-ng/1.52.0/lib/libespeak-ng.dylib
fi

python3 infer/infer.py \
    --lrc-path infer/example/eg_en_full.lrc \
    --ref-prompt "classical genres, hopeful mood, piano." \
    --audio-length 95 \
    --repo-id ASLP-lab/DiffRhythm-1_2 \
    --output-dir infer/example/output \
    --chunked \
    --batch-infer-num 5

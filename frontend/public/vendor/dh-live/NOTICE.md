# DH_live prototype assets

Upstream: https://github.com/kleinlee/DH_live
Revision: 4467e97cd97194c2c54762043cf121c6d313db12

The upstream English README declares MIT licensing, and separately requires
avatar authorization for commercial web use / logo removal. This academic
prototype preserves upstream marks. Example people are demonstration assets,
not Socratia jury identities. Confirm rights before wider redistribution or
replace them with authorized recordings. No logo removal is performed.

Copied runtime: DHLiveMini.js, DHLiveMini.wasm, MiniLive2.js, pako.min.js;
example avatar packages assets and assets2; common texture.
There are three renderer slots. Alex/Elena use upstream examples; Daniel uses
a fictional image generated for Socratia and processed with upstream
DINet_mini, SCRFD and FaceLandmarker checkpoints. See docs/jury-avatar-generation.md.
Additional unused upstream examples assets3/assets5 are not selected by the player.
MiniLive2.js has one adaptation: its animation frame handle is retained so
Socratia can cancel it when pausing, avoiding duplicate loops on resume.
An optional recoloring shader from the earlier duplicate demo remains disabled.
The MatesX mark is preserved.
player.html and bridge.js are Socratia integration files.

listening.mp4 clips are offline facial-motion derivatives of the corresponding
neutral frames, generated with FasterLivePortrait revision
8aad3602177547aaa5e4beec0c3ef5b7944e7a1f and its public ONNX models.
Original identity assets and marks remain attributed as above. The animation
code is MIT; pretrained model terms remain separate. Academic prototype use.
Model provenance and CPU conversion: docs/jury-facial-motion.md.

On 2026-10-18, all three speaking bases (01.mp4 and combined_data.json.gz)
were regenerated from these animated listening clips in a remote Colab T4
runtime. Each base contains 200 frames at 25 FPS with matching facial data.
No local model inference is required for creating these assets now.

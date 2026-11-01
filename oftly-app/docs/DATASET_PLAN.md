# Datasets, models and local training plan

Status legend: VERIFIED = read from an official repo this session. UNVERIFIED = not confirmed; do not download.
Dataset licence, licence of the images inside it, and model-weight licence are three separate questions.

## Datasets
| Dataset | Source checked | What was verified | Decision |
|---|---|---|---|
| Fashionpedia | official cvdfoundation README (download links); licence text only via a Hugging Face mirror card | Annotations stated as CC BY 4.0 (mirror card, not the official repo; repo has no LICENSE file). Annotation format carries a per-image `license` field, so images are not uniformly licensed. Official links: train2020.zip, val_test2020.zip, annotation JSONs on CVDF S3. 46,781 images (mirror card). File sizes NOT verified (S3 unreachable from my sandbox). | **OK for local evaluation only**, after you read the licence on https://fashionpedia.github.io/home. Do not redistribute images. |
| Fashion-MNIST | official repo | MIT licence. 28x28 grayscale. | OK, but only to smoke-test code. Useless for real wardrobe quality. |
| Polyvore Outfits (Vasileva et al.) | official repo | Code is BSD-3. README says dataset is ~6 GB hosted on Hugging Face. **No dataset licence stated**; images come from a third-party site. | **Hold.** Not needed: learn compatibility from your own feedback instead. |
| ModaNet | official repo + LICENSE | Annotations CC BY-NC 4.0; images from PaperDoll/Chictopia. | **Avoid** (non-commercial; street photos, poor fit). |
| DeepFashion2 | official repo | Access via Google Drive + a request form for the unzip password. No LICENSE file; terms are in the form, which I did not read. | **Hold** until you read the form terms. |
| ABO | arXiv paper, AWS registry | **Conflicting**: paper and AWS registry say CC BY-NC 4.0; a third-party card claims a 2023 relicense to CC BY 4.0. Could not open the bucket. Mostly household objects, not fashion. | **Avoid** (low relevance, licence unresolved). |
| DeepFashion, Fashion-Gen, Fashion Product Images (Kaggle), Polyvore (Han et al.) | not checked | UNVERIFIED. | **Do not download** until checked. |

## Models
| Model | Verified | Open question |
|---|---|---|
| FashionCLIP (patrickjohncyh) | GitHub code is MIT. README says v2.0 fine-tunes laion CLIP ViT-B/32. | Weight licence on the Hugging Face model card and the base checkpoint's licence: UNVERIFIED (HF unreachable here). Check before use. |
| Marqo FashionSigLIP, generic OpenCLIP | not checked | UNVERIFIED. |
Local feasibility: a ViT-B/32 CLIP-class model is expected to run on a MacBook CPU/Apple GPU (estimate, not measured). Please tell me your chip and RAM.

## Plan (smallest useful first)
0. **No download needed.** Existing Pillow colour extraction stays the default.
1. **Zero-shot suggestions**: optional `OFTLY_ML=1` module `backend/app/vision.py`: image -> embedding -> text-prompt scores for category/pattern. Output is labelled "suggested", never written to confirmed fields.
2. **Own evaluation set**: you photograph/label 100-200 of your own garments. Metrics: top-1 accuracy and per-category macro-F1 against OFTLY's taxonomy. Optional extra: Fashionpedia val images, evaluation only.
3. **Linear probe** (logistic regression on frozen embeddings) using labels you confirm in-app. Seconds on a laptop; no training from scratch.
4. **Learned compatibility** only from your accept/reject/worn feedback, added as `parts["learned"]` in `engine.score_outfit`. No outfit dataset required.
Gate: a suggestion is shown only if measured on held-out data and above a confidence threshold; no accuracy claims otherwise.
Not claimed: fabric, warmth, thickness or breathability from images. Those need user input or product metadata.

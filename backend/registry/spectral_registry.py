"""Pinned Phase1 asset identities and hashes for the common Mach6 freeze.

Metadata only. Hash baselines come from data_asset_inventory.json and agree
with the frozen SHA256_MANIFEST.json; no scientific code is imported.
"""

SCIENTIFIC_ROOT = "D:/Paper/passage6"
FREEZE_DIR = "experiments/linear_perturbation_analysis/FREEZE"
REGISTRY_REVISION = "spectral-registry-v1"
DATA_REVISION = "linear-perturbation-freeze-v1"
COLLECTION_ID = "spectrum.common-mach6"
BASE_RESULT_ID = "spectrum.common-mach6.base"
MASK_ID = "mask.spectrum.fixed-shock-cells"
METHOD_NAME = "cross_mode_ec_unified_v1"
METHOD_HASH = "98776078f19fa4b31826e88e8851222f217210c3c2ae341d68aeb60aad3a27e0"

# Relative name: (Phase1 asset ID, pinned SHA256, role, format, upstream status).
ASSETS = {
    'config.json': (
        'asset_99701f5ec82d', 'a1fccc9b1664ff3486cd3105e9790e79f8d388e5fb93697aa869617b36108cf0',
        'CONFIG', 'JSON', 'FROZEN_VERIFIED'),
    'method_identity.json': (
        'asset_da31ed0fd36c', 'e2426ee3036d8761907da47e008ee4f430a3aead6fa1c57bc8133ee6b3fa8eb8',
        'METHOD', 'JSON', 'FROZEN_VERIFIED'),
    'SHA256_MANIFEST.json': (
        'asset_e1b9ba43e984', '04174ca1db34b911636a9ac90522b9202401fc3c14fcfc093d0f1e6b1a597bcb',
        'FREEZE', 'JSON', 'AVAILABLE_UNVERIFIED'),
    'validity_gates.json': (
        'asset_46b73972e076', 'ad6bd90a4905ef81cea797d0aee4905cdaa3fccba97c51a5acd3084144fddcb2',
        'ANALYSIS', 'JSON', 'FROZEN_VERIFIED'),
    'base_state/base_state_audit.json': (
        'asset_d23dcd878d59', '809fdba2799c332238db3b222c6a4686719b131e771387e8a84d834b4aa74d69',
        'ANALYSIS', 'JSON', 'FROZEN_VERIFIED'),
    'base_state/base_state.npz': (
        'asset_6c6b9c35c1dc', '2c4c096401264b6a61a0df2325135a1159c0e2d4e281fb929eaa085cf8baf862',
        'DATA', 'NPZ', 'FROZEN_VERIFIED'),
    'spectrum/shock_mask.json': (
        'asset_3b8c484e13f4', '28cd62a0d6212763f13ddc677be457b6db0547244eb8ad9f57079a6e40a5ac09',
        'MASK', 'JSON', 'FROZEN_VERIFIED'),
    'production_source/solver/fluxes/cross_mode_ec_unified_v1.py': (
        'asset_7b3c12f093bc', '98776078f19fa4b31826e88e8851222f217210c3c2ae341d68aeb60aad3a27e0',
        'METHOD', 'PY', 'FROZEN_VERIFIED'),
    'scripts/common.py': (
        'asset_076aa4872485', '8b02d314db4367e0c248c9239018f2caeecdf8e946eb88ad14e0c3551139f4de',
        'METHOD', 'PY', 'FROZEN_VERIFIED'),
    'scripts/spectrum_scan.py': (
        'asset_86b8922823c0', 'bb65c1c0d0d43c2440a01e0a9082ae845edd68e6d8791685e75c8c2448c39463',
        'METHOD', 'PY', 'FROZEN_VERIFIED'),
    'scripts/cfd_validation.py': (
        'asset_9e69ab916a06', '880d7d42ae88a5782b54ea622a61e169e8c9fc314ffd763370e3062da9eebc09',
        'METHOD', 'PY', 'FROZEN_VERIFIED'),
    'spectrum/spectral_summary.csv': (
        'asset_e45cd83f9cbc', '92cf35b8f158e5795c18dd70220505e2a829c7ccb29aafae2531a512a6ae3b39',
        'DATA', 'CSV', 'FROZEN_VERIFIED'),
    'spectrum/eigenvalues.npz': (
        'asset_bf6eb2f08545', '064c478d63e317a8cfc9e885f514d240183167f72998a8e28abe410e31c07b93',
        'DATA', 'NPZ', 'FROZEN_VERIFIED'),
    'spectrum/right_eigenvectors.npz': (
        'asset_8f3a3aa5c631', '49d59a9d5f701e0ec061bf39f7ffc1614bdd0598b41ef4af0e1929b5eb13d088',
        'DATA', 'NPZ', 'FROZEN_VERIFIED'),
    'spectrum/left_eigenvectors.npz': (
        'asset_9e76bb48e872', '1b181bbc65e13775df4cce9f8a06b4a9930d50f308c10e18286196c1083183b6',
        'DATA', 'NPZ', 'FROZEN_VERIFIED'),
    'spectrum/leading_primitive_amplitude_profiles.npz': (
        'asset_f53235bc1bf3', 'd5e9cbf57097942c3c6a96e0ef5349c9841c8cbc82864942317649392b132081',
        'DATA', 'NPZ', 'FROZEN_VERIFIED'),
    'spectrum/eigenvector_metrics.csv': (
        'asset_0169e668f7df', '0d5e2e848048a6f825bb82b3ab301f8991f13324bc23ef6b4e38f3fe951d4a25',
        'DATA', 'CSV', 'FROZEN_VERIFIED'),
    'cfd_validation/validation_summary.csv': (
        'asset_eef93c1945fd', '9205ee2d63061b13488dfc6f52b3786cc7c5e30e553cf77f6c8a387759c34cb3',
        'DATA', 'CSV', 'FROZEN_VERIFIED'),
    'cfd_validation/mode_selection.json': (
        'asset_0169359b708b', 'cfbbaa8a6d121568a05a336e029b33210c1b07479ee87d3a99dd62b7d1812131',
        'CONFIG', 'JSON', 'FROZEN_VERIFIED'),
    'cfd_validation/runs/m01_q0p000_eps1e-04.csv': (
        'asset_f8ab2dd87368', 'bec63bf9e85db408fe3757fbeb6d2256456ff0d25f9a75fac5b3263e875dad34',
        'DATA', 'CSV', 'FROZEN_VERIFIED'),
    'cfd_validation/runs/m01_q0p000_eps1e-05.csv': (
        'asset_f836b45ccc9a', '45614486566b3a2c7c0c1c6b1d121f9cc96a452032b0a3e15803163350d51dcb',
        'DATA', 'CSV', 'FROZEN_VERIFIED'),
    'cfd_validation/runs/m01_q0p000_eps1e-06.csv': (
        'asset_9a1b75dbedfe', '8e78d116e3a5dfb0e3d0119c61172a861c291d7717595a66153b993d92a34f81',
        'DATA', 'CSV', 'FROZEN_VERIFIED'),
    'cfd_validation/runs/m01_q0p396_eps1e-04.csv': (
        'asset_9c16d3007b99', '8e13daca0bcd4b8d64fc8761e24d593000929fee6d3cd280bd71bec8cc683c25',
        'DATA', 'CSV', 'FROZEN_VERIFIED'),
    'cfd_validation/runs/m01_q0p396_eps1e-05.csv': (
        'asset_263bdb260496', '3d609f8228233381614da7c8e211c47d5215cfd17fc20ee395a11d4a4ee67413',
        'DATA', 'CSV', 'FROZEN_VERIFIED'),
    'cfd_validation/runs/m01_q0p396_eps1e-06.csv': (
        'asset_4de2046b7a69', '252bf17057927adbd45e157c44bde370831063b1623956be4ce6c29e0a73136d',
        'DATA', 'CSV', 'FROZEN_VERIFIED'),
    'cfd_validation/runs/m04_q0p000_eps1e-04.csv': (
        'asset_2704e3683db8', '0a561e745e811b75b06959599b2e6b08bb43f3bc1f47d5c20a87567520b3161e',
        'DATA', 'CSV', 'FROZEN_VERIFIED'),
    'cfd_validation/runs/m04_q0p000_eps1e-05.csv': (
        'asset_b9803fd2f22b', '9195f2307439f0ed7d181178fa8c6bf9ef4cd3795808bb0ba3151f5390894b45',
        'DATA', 'CSV', 'FROZEN_VERIFIED'),
    'cfd_validation/runs/m04_q0p000_eps1e-06.csv': (
        'asset_022af60ea486', 'd265d759800e1459b3e95257927341089e7b9751a3b21a750b25a146a35cf151',
        'DATA', 'CSV', 'FROZEN_VERIFIED'),
    'cfd_validation/runs/m04_q0p396_eps1e-04.csv': (
        'asset_0ff9bcdb0574', '0c5fdb5c0dd9b7bb8d40cb57ed52be7cafae83ed7913b366c208f2aad49619e5',
        'DATA', 'CSV', 'FROZEN_VERIFIED'),
    'cfd_validation/runs/m04_q0p396_eps1e-05.csv': (
        'asset_76ad36a52f2d', '4575e91e8312837f58944567ce5b7149d5da17540156f856368a4d291478afdf',
        'DATA', 'CSV', 'FROZEN_VERIFIED'),
    'cfd_validation/runs/m04_q0p396_eps1e-06.csv': (
        'asset_0f9e83e747a6', '2f526a298a524b4898488ac7a0e8dd6a302ce6a2fe29940929443dc7545276e0',
        'DATA', 'CSV', 'FROZEN_VERIFIED'),
    'cfd_validation/runs/m08_q0p000_eps1e-04.csv': (
        'asset_11b5858d08b8', '2666ddeb2be325790b9870da23746c3fd6a78eb063b5a561d7781cb40b094c6e',
        'DATA', 'CSV', 'FROZEN_VERIFIED'),
    'cfd_validation/runs/m08_q0p000_eps1e-05.csv': (
        'asset_35a9b515d127', 'afa3242787892d68a7d2c3a33e93f6b57f28b8c5d1edb202dd7a5ce8f0756d5c',
        'DATA', 'CSV', 'FROZEN_VERIFIED'),
    'cfd_validation/runs/m08_q0p000_eps1e-06.csv': (
        'asset_29cd60159792', 'acf17fbfd6447812c1d177144c51f216bb1f1044c5aaaede0172c4b6c70789cc',
        'DATA', 'CSV', 'FROZEN_VERIFIED'),
    'cfd_validation/runs/m08_q0p396_eps1e-04.csv': (
        'asset_097eed69b99d', 'f326f0493447b691a1acaa5aca8af56a977b225fad9b3f84f60268e020149777',
        'DATA', 'CSV', 'FROZEN_VERIFIED'),
    'cfd_validation/runs/m08_q0p396_eps1e-05.csv': (
        'asset_c8693474d820', '287e7847862e6fd254f6f3b1d1750dc400b6f931eeb9fc4d8d896491480bef66',
        'DATA', 'CSV', 'FROZEN_VERIFIED'),
    'cfd_validation/runs/m08_q0p396_eps1e-06.csv': (
        'asset_a03161a3d8e9', 'fa78ffb40bceb50d8fc29aa8081a5fcba5f61ea6f5b81b4422bd89f19e34fbf0',
        'DATA', 'CSV', 'FROZEN_VERIFIED'),
    'cfd_validation/runs/m12_q0p000_eps1e-04.csv': (
        'asset_c20d494ee60f', '621c470a377afbcdbcf49dac436b5fac156777c299d37d8218b8ecb6d3c20f7e',
        'DATA', 'CSV', 'FROZEN_VERIFIED'),
    'cfd_validation/runs/m12_q0p000_eps1e-05.csv': (
        'asset_71b9f75abfbf', '989a60380ddc1a9761caa476db2f0f334b5eb04c7b072f60377f2a2acf5f261f',
        'DATA', 'CSV', 'FROZEN_VERIFIED'),
    'cfd_validation/runs/m12_q0p000_eps1e-06.csv': (
        'asset_1dc86f60816b', '9534b56702bb69b9efaacc32a9135640850b381cfb5ae30039ab4e1ec07e8cee',
        'DATA', 'CSV', 'FROZEN_VERIFIED'),
    'cfd_validation/runs/m12_q0p396_eps1e-04.csv': (
        'asset_7edf04ffab92', 'c1ff21c97f86e0fc2d50cc0754023cb6f1d61e144329877aa182a81106efa715',
        'DATA', 'CSV', 'FROZEN_VERIFIED'),
    'cfd_validation/runs/m12_q0p396_eps1e-05.csv': (
        'asset_02dc9a12fea7', 'e03ab4ef8b9c72a13881009cda6a09c6a09a2d56f26efdd84c7fd1da140b1697',
        'DATA', 'CSV', 'FROZEN_VERIFIED'),
    'cfd_validation/runs/m12_q0p396_eps1e-06.csv': (
        'asset_1a0f5e2dc22b', 'a999cb9b07918e188da90cfebe6c1f91dddc09f2fe27c07acc4144a457b17cb0',
        'DATA', 'CSV', 'FROZEN_VERIFIED'),
}

DATASETS = {
    "spectrum.q-0.000": 0.0,
    "spectrum.q-0.132": 0.132,
    "spectrum.q-0.264": 0.264,
    "spectrum.q-0.396": 0.396,
}

# Run identities use original basenames, never user-provided history paths.
RUNS = {
    "modal-validation.m01_q0p000_eps1e-04": (1, 0.0, 0.0001, 'cfd_validation/runs/m01_q0p000_eps1e-04.csv'),
    "modal-validation.m01_q0p000_eps1e-05": (1, 0.0, 1e-05, 'cfd_validation/runs/m01_q0p000_eps1e-05.csv'),
    "modal-validation.m01_q0p000_eps1e-06": (1, 0.0, 1e-06, 'cfd_validation/runs/m01_q0p000_eps1e-06.csv'),
    "modal-validation.m01_q0p396_eps1e-04": (1, 0.396, 0.0001, 'cfd_validation/runs/m01_q0p396_eps1e-04.csv'),
    "modal-validation.m01_q0p396_eps1e-05": (1, 0.396, 1e-05, 'cfd_validation/runs/m01_q0p396_eps1e-05.csv'),
    "modal-validation.m01_q0p396_eps1e-06": (1, 0.396, 1e-06, 'cfd_validation/runs/m01_q0p396_eps1e-06.csv'),
    "modal-validation.m04_q0p000_eps1e-04": (4, 0.0, 0.0001, 'cfd_validation/runs/m04_q0p000_eps1e-04.csv'),
    "modal-validation.m04_q0p000_eps1e-05": (4, 0.0, 1e-05, 'cfd_validation/runs/m04_q0p000_eps1e-05.csv'),
    "modal-validation.m04_q0p000_eps1e-06": (4, 0.0, 1e-06, 'cfd_validation/runs/m04_q0p000_eps1e-06.csv'),
    "modal-validation.m04_q0p396_eps1e-04": (4, 0.396, 0.0001, 'cfd_validation/runs/m04_q0p396_eps1e-04.csv'),
    "modal-validation.m04_q0p396_eps1e-05": (4, 0.396, 1e-05, 'cfd_validation/runs/m04_q0p396_eps1e-05.csv'),
    "modal-validation.m04_q0p396_eps1e-06": (4, 0.396, 1e-06, 'cfd_validation/runs/m04_q0p396_eps1e-06.csv'),
    "modal-validation.m08_q0p000_eps1e-04": (8, 0.0, 0.0001, 'cfd_validation/runs/m08_q0p000_eps1e-04.csv'),
    "modal-validation.m08_q0p000_eps1e-05": (8, 0.0, 1e-05, 'cfd_validation/runs/m08_q0p000_eps1e-05.csv'),
    "modal-validation.m08_q0p000_eps1e-06": (8, 0.0, 1e-06, 'cfd_validation/runs/m08_q0p000_eps1e-06.csv'),
    "modal-validation.m08_q0p396_eps1e-04": (8, 0.396, 0.0001, 'cfd_validation/runs/m08_q0p396_eps1e-04.csv'),
    "modal-validation.m08_q0p396_eps1e-05": (8, 0.396, 1e-05, 'cfd_validation/runs/m08_q0p396_eps1e-05.csv'),
    "modal-validation.m08_q0p396_eps1e-06": (8, 0.396, 1e-06, 'cfd_validation/runs/m08_q0p396_eps1e-06.csv'),
    "modal-validation.m12_q0p000_eps1e-04": (12, 0.0, 0.0001, 'cfd_validation/runs/m12_q0p000_eps1e-04.csv'),
    "modal-validation.m12_q0p000_eps1e-05": (12, 0.0, 1e-05, 'cfd_validation/runs/m12_q0p000_eps1e-05.csv'),
    "modal-validation.m12_q0p000_eps1e-06": (12, 0.0, 1e-06, 'cfd_validation/runs/m12_q0p000_eps1e-06.csv'),
    "modal-validation.m12_q0p396_eps1e-04": (12, 0.396, 0.0001, 'cfd_validation/runs/m12_q0p396_eps1e-04.csv'),
    "modal-validation.m12_q0p396_eps1e-05": (12, 0.396, 1e-05, 'cfd_validation/runs/m12_q0p396_eps1e-05.csv'),
    "modal-validation.m12_q0p396_eps1e-06": (12, 0.396, 1e-06, 'cfd_validation/runs/m12_q0p396_eps1e-06.csv'),
}

def dataset_id(q):
    return next(key for key, value in DATASETS.items() if value == q)

def record_id(dataset, mode):
    return f"{dataset}.mode-{mode:02d}"

def eigenmode_id(dataset, mode, side, rank, representation="COMPLEX_VECTOR", component="stored_vector"):
    return f"{record_id(dataset, mode)}.{side.lower()}.rank-{rank:02d}.{representation.lower()}.{component}"

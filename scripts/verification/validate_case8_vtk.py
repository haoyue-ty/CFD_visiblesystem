"""Independent VTK-library acceptance (analysis-env), not just XML validation."""
import argparse
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
from vtkmodules.vtkIOXML import vtkXMLImageDataReader
from vtkmodules.util.numpy_support import vtk_to_numpy


def validate(root, reference):
    info = json.loads((reference/'reference.json').read_text(encoding='utf-8'))
    nx, ny, dx, dy = (info[k] for k in ('nx','ny','dx','dy'))
    pvd = ET.parse(root/'exports/visualization/timeseries.pvd').findall('.//DataSet')
    assert len(pvd) == len(info['snapshots'])
    checks=[]
    for row, snapshot in zip(pvd,info['snapshots']):
        assert float(row.attrib['timestep']) == snapshot['time']
        file=root/'exports/visualization'/row.attrib['file']
        assert file.is_file()
        reader=vtkXMLImageDataReader()
        reader.SetFileName(str(file)); reader.Update()
        assert reader.GetErrorCode() == 0
        image=reader.GetOutput()
        assert image.GetNumberOfCells() == nx*ny
        assert image.GetDimensions() == (nx+1,ny+1,2)
        assert image.GetPointData().GetNumberOfArrays() == 0
        assert image.GetCellData().GetNumberOfArrays() == 9
        assert image.GetFieldData().GetArray('TimeValue').GetTuple1(0) == snapshot['time']
        np.testing.assert_allclose(image.GetOrigin(),(info['x0'],info['y0'],-min(dx,dy)/2),rtol=0,atol=0)
        np.testing.assert_allclose(image.GetSpacing(),(dx,dy,min(dx,dy)),rtol=0,atol=0)
        # Verify the actual first/last VTK cell center, detecting half-cell shifts and flips.
        for index, expected_center in ((0,(info['x0']+dx/2,info['y0']+dy/2,0)),
                (nx*ny-1,(info['x0']+(nx-.5)*dx,info['y0']+(ny-.5)*dy,0))):
            bounds=image.GetCell(index).GetBounds()
            center=[(bounds[k]+bounds[k+1])/2 for k in (0,2,4)]
            np.testing.assert_allclose(center,expected_center,rtol=0,atol=1e-14)
        with np.load(reference/(snapshot['snapshot_id']+'.npz'),allow_pickle=False) as expected:
            errors={}
            for name in expected.files:
                array=image.GetCellData().GetArray(name)
                assert array is not None
                values=vtk_to_numpy(array).reshape(ny,nx)
                # Writer is lossless Float64. Reference fields reuse the production postprocessor.
                np.testing.assert_allclose(values,expected[name],rtol=0,atol=0)
                errors[name]=float(np.max(np.abs(values-expected[name])))
        checks.append({'file':file.name,'time':snapshot['time'],'cells':image.GetNumberOfCells(),'max_abs_errors':errors})
    assert all(float(a.attrib['timestep']) < float(b.attrib['timestep']) for a,b in zip(pvd,pvd[1:]))
    return {'status':'PASS','reader':'vtkXMLImageDataReader','rtol':0,'atol':0,'frames':checks}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run-dir',type=Path,required=True)
    parser.add_argument('--reference',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=validate(args.run_dir,args.reference)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(f"VTK ACCEPTANCE PASS: {len(result['frames'])} real frames, all 9 fields exact, cell centers and dimensions correct")


if __name__=='__main__': main()

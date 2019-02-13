from xmldiff import main

# differ = diff.Differ()
diff = main.diff_files('checksum-test-sample/smith_67952_MODS.xml', 'checksum-test-sample/smith_67952_MODS-remote.xml',
                       diff_options={'F': 0.5, 'ratio_mode': 'fast'})
import pdb; pdb.set_trace()

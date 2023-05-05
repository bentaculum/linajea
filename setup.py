from setuptools import setup

setup(
        name='linajea',
        version='1.5',
        description='Lineage Tracking in 4D Microscopy Volumes.',
        url='https://github.com/funkelab/linajea',
        author='Jan Funke, Caroline Malin-Mayor, Peter Hirsch',
        author_email='funkej@janelia.hhmi.org',
        license='MIT',
        packages=[
            'linajea',
            'linajea.config',
            'linajea.evaluation',
            'linajea.gunpowder_nodes',
            'linajea.prediction',
            'linajea.process_blockwise',
            'linajea.tracking',
            'linajea.training',
            'linajea.utils',
        ],
        scripts=[
            'run_scripts/linajea'
        ],
        python_requires=">=3.8"
)

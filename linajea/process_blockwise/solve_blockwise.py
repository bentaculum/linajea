import daisy
import json
from linajea import CandidateDatabase
from .daisy_check_functions import check_function, write_done
from linajea.tracking import TrackingParameters, track
import logging
import os
import time

logger = logging.getLogger(__name__)


def solve_blockwise(
        db_host,
        db_name,
        sample,
        num_workers=8,
        frames=None,
        from_scratch=False,
        **kwargs):

    parameters = TrackingParameters(**kwargs)
    block_size = daisy.Coordinate(parameters.block_size)
    context = daisy.Coordinate(parameters.context)

    data_dir = '../01_data'

    # get absolute paths
    if os.path.isfile(sample) or sample.endswith((".zarr", ".n5")):
        sample_dir = os.path.abspath(os.path.join(data_dir,
                                                  os.path.dirname(sample)))
    else:
        sample_dir = os.path.abspath(os.path.join(data_dir, sample))

    # get ROI of source
    with open(os.path.join(sample_dir, 'attributes.json'), 'r') as f:
        attributes = json.load(f)

    voxel_size = daisy.Coordinate(attributes['resolution'])
    shape = daisy.Coordinate(attributes['shape'])
    offset = daisy.Coordinate(attributes['offset'])
    source_roi = daisy.Roi(offset, shape*voxel_size)

    # determine parameters id from database
    graph_provider = CandidateDatabase(
        db_name,
        db_host)
    parameters_id = graph_provider.get_parameters_id(parameters)

    if from_scratch:
        graph_provider.set_parameters_id(parameters_id)
        graph_provider.reset_selection()

    # limit to specific frames, if given
    if frames:
        logger.info("Solving in frames %s" % frames)
        begin, end = frames
        crop_roi = daisy.Roi(
            (begin, None, None, None),
            (end - begin, None, None, None))
        source_roi = source_roi.intersect(crop_roi)

    block_write_roi = daisy.Roi(
        (0, 0, 0, 0),
        block_size)
    block_read_roi = block_write_roi.grow(
        context,
        context)
    total_roi = source_roi.grow(
        context,
        context)

    logger.info("Solving in %s", total_roi)

    daisy.run_blockwise(
        total_roi,
        block_read_roi,
        block_write_roi,
        process_function=lambda b: solve_in_block(
            db_host,
            db_name,
            parameters,
            b,
            parameters_id),
        check_function=lambda b: check_function(
            b,
            'solve_' + str(parameters_id),
            db_name,
            db_host),
        num_workers=num_workers,
        fit='shrink')

    logger.info("Finished solving, parameters id is %s", parameters_id)


def solve_in_block(db_host, db_name, parameters, block, parameters_id):

    logger.debug("Solving in block %s", block)

    graph_provider = CandidateDatabase(
        db_name,
        db_host,
        mode='r+',
        parameters_id=parameters_id)
    start_time = time.time()
    graph = graph_provider.get_graph(
            block.read_roi,
            edge_attrs=["prediction_distance",
                        "distance",
                        graph_provider.selected_key]
            )

    # remove dangling nodes and edges
    dangling_nodes = [
        n
        for n, data in graph.nodes(data=True)
        if 't' not in data
    ]
    graph.remove_nodes_from(dangling_nodes)

    num_nodes = graph.number_of_nodes()
    num_edges = graph.number_of_edges()
    logger.info("Reading graph with %d nodes and %d edges took %s seconds"
                % (num_nodes, num_edges, time.time() - start_time))

    if num_edges == 0:
        logger.info("No edges in roi %s. Skipping"
                    % block.read_roi)
        write_done(block, 'solve_' + str(parameters_id), db_name, db_host)
        return 0

    track(graph, parameters, graph_provider.selected_key)
    start_time = time.time()
    graph.update_edge_attrs(
            block.write_roi,
            attributes=[graph_provider.selected_key])
    logger.info("Updating attribute %s for %d edges took %s seconds"
                % (graph_provider.selected_key,
                   num_edges,
                   time.time() - start_time))
    write_done(block, 'solve_' + str(parameters_id), db_name, db_host)
    return 0
import numpy as np
from math import ceil
import matplotlib.pyplot as plt
import matplotlib

# This import line is not explicitly used, but do not remove it!
# It is nescessary to be able to perform
from mpl_toolkits.mplot3d import Axes3D

# todo: move to a more elaborate plotting concept
# like https://scipy-cookbook.readthedocs.io/items/Matplotlib_UnfilledHistograms.html for unfilled histograms
# todo: more flexible signature?
def plot_histogram(ax: plt.axes,
                   binning: np.array,
                   contents: np.array,
                   normalized=False,
                   *args,
                   **kwargs) -> None:
    """ Plots histogram

    Args:
        ax: Axes of a plot
        binning: numpy array of bin edges
        contents: numpy array of bin contents
        normalized: If true, the plotted histogram will be normalized

    Returns:
        None
    """
    assert len(binning.shape) == len(contents.shape) == 1
    n = binning.shape[0] - 1  # number of bins
    assert n == contents.shape[0]
    assert n >= 1
    mpoints = (binning[1:] + binning[:-1]) / 2

    if normalized:
        values = contents / sum(contents)
    else:
        values = contents

    return ax.hist(mpoints,
                   bins=binning,
                   weights=values,
                   linewidth=0,
                   *args,
                   **kwargs
    )





def plot_clusters(df,
                  cols,
                  clusters=None,
                  colors=None,
                  markers=None,
                  max_subplots=16,
                  max_cols=4,
                  figsize=(4, 4),
                  debug=False,
                  **kwargs):
    """Creates 2D plots (slices) of the clusters.

    Args:
        df: Dataframe
        cols: List of the column names to plot
        clusters: List of clusters to include
        colors: List of colors to use for the different clusters
        markers: List of colors to use for the different clusters
        max_subplots: Maximal number of different plots/slices
        figsize: Size of each subplot (tuple)
        debug: debug enabled?
        kwargs: arguments for plt.scatter

    Returns:
        matplotlib.pyplot.figure (unless inline matplotlib is used, then None)
    """
    def deb(*args, **kwargs):
        """ For debugging this function """
        if debug:
            print(*args, **kwargs)

    assert(2 <= len(cols) <= 3)

    # *** 1. find all relevant wilson coefficients that are not ***
    # ***    axes on the plots (called dofs)                    ***

    dofs = []
    relevant_dofs = []
    for col in ['l', 'r', 'sl', 'sr', 't']:
        if col not in cols:
            dofs.append(col)
            if len(df[col].unique()) >= 2:
                relevant_dofs.append(col)
    deb("dofs = {}, relevant_dofs = {}".format(dofs, relevant_dofs))

    # find all unique value combinations of these columns
    df_dofs = df[dofs].drop_duplicates().sort_values(dofs)
    df_dofs.reset_index(inplace=True)
    deb("number of subplots = {}".format(len(df_dofs)))

    # *** 2. reduce the number of subplots by only sampling  **
    # ***    several points of the above Wilson coeffs       **

    if len(df_dofs) > max_subplots:
        steps_per_dof = int(max_subplots ** (1 / len(relevant_dofs)))
        deb("number of steps per dof", steps_per_dof)
        for col in relevant_dofs:
            allowed_values = df_dofs[col].unique()
            indizes = list(set(np.linspace(0, len(allowed_values)-1,
                                           steps_per_dof).astype(int)))
            allowed_values = allowed_values[indizes]
            df_dofs = df_dofs[df_dofs[col].isin(allowed_values)]
        deb("number of subplots left after "
            "subsampling = {}".format(len(df_dofs)))

    nsubplots = len(df_dofs)


    # *** 3. Set up subplots ***

    ncols = min(max_cols, len(df_dofs))
    nrows = ceil(len(df_dofs)/ncols)

    deb("nrows = {}, ncols = {}".format(nrows, ncols))

    # squeeze keyword: https://stackoverflow.com/questions/44598708/
    # do not share axes, that makes problems if the grid is incomplete
    subplots_args = {
        "nrows":nrows,
        "ncols": ncols,
        "figsize": (ncols*figsize[0], nrows*figsize[1]),
        "squeeze": False,
    }
    if len(cols) == 3:
        subplots_args["subplot_kw"] = {'projection': '3d'}
    fig, axs = plt.subplots(**subplots_args)
    axli = axs.flatten()

    # note: axs contains all axes (subplots) as a 2D grid,
    #       axsli contains the same objects but as a
    #       simple list (easier to iterate over)

    ihidden = nrows*ncols - nsubplots
    icol_hidden = ncols - ihidden
    deb("ihidden = {}".format(ihidden))
    deb("icol_hidden = {}".format(icol_hidden))
    if len(cols) == 2:
        for isubplot in range(nrows * ncols):
            irow = isubplot//ncols
            icol = isubplot % ncols

            if isubplot >= nsubplots:
                deb("hiding", irow, icol)
                axli[isubplot].set_visible(False)

            if icol == 0:
                axli[isubplot].set_ylabel(cols[1])
            else:
                axli[isubplot].set_yticklabels([])

            if irow == nrows - 2 and icol >= icol_hidden:
                axli[isubplot].set_xlabel(cols[0])
            elif irow == nrows - 1 and icol <= icol_hidden:
                axli[isubplot].set_xlabel(cols[0])
            else:
                axli[isubplot].set_xticklabels([])

    else:
        for isubplot in range(nsubplots):
            axli[isubplot].set_xlabel(cols[0])
            axli[isubplot].set_ylabel(cols[1])
            axli[isubplot].set_zlabel(cols[2])

    # set the xrange explicitly in order to not depend
    # on which clusters are shown etc.

    def get_lims(ax_no, stretch=0.1):
        """ Get the limits with a bit of padding """
        mi = min(df[cols[ax_no]].values)
        ma = max(df[cols[ax_no]].values)
        d = ma-mi
        pad = stretch * d
        return mi-pad, ma+pad

    for isubplot in range(nsubplots):
        axli[isubplot].set_xlim(get_lims(0))
        axli[isubplot].set_ylim(get_lims(1))
        if len(cols) == 3:
            axli[isubplot].set_zlim(get_lims(2))


    # *** 4. MISC preparations ***

    if not colors:
        colors = ["red", "green", "blue", "black", "orange","pink", ]
    if not markers:
        markers = ["o", "v", "^", "v", "<", ">"]
    if not clusters:
        # plot all
        clusters = list(df['cluster'].unique())

    # *** 5. Plot ***

    for isubplot in range(nsubplots):
        title = " ".join("{}={:.2f}".format(key, df_dofs.iloc[isubplot][key])
                         for key in relevant_dofs)
        axli[isubplot].set_title(title)
        for cluster in clusters:
            df_cluster = df[df['cluster'] == cluster]
            for col in relevant_dofs:
                df_cluster = df_cluster[df_cluster[col] ==
                                        df_dofs.iloc[isubplot][col]]
            axli[isubplot].scatter(
                *[df_cluster[col] for col in cols],
                color=colors[cluster-1 % len(colors)],
                marker=markers[cluster-1 % len(markers)],
                label=cluster,
                **kwargs
            )
    if 'inline' not in matplotlib.get_backend():
        return fig

#!/usr/bin/env python3

# std
import json
import logging
import pandas as pd
from pathlib import PurePath, Path
from typing import Union

# ours
from bclustering.util.metadata import nested_dict
from bclustering.util.log import get_logger
from bclustering.util.cli import handle_overwrite


class DFMD(object):
    # fixme: Use @classmethod instead of so much logic?
    def __init__(self, *args, log=None, **kwargs):
        """ This class bundles dataframe together with metadata and options
        to load from and write these two to files.

        There are five different ways to initialize this class:

        1. Initialize it empty: ``DFMD()``.
        2. From another DFMD object ``my_dfmd``: ``DFMD(my_dfmd)`` or
            ``DFMD(dfmd=my_dfmd)``.
        3. From a directory path and a project name:
            ``DFMD("path/to/io", "my_name")`` or
            ``DFMD(directory="path/to/io", name="my_name"``
        4. From a dataframe and a metadata object (a nested dictionary like
            object) or paths to corresponding files:
            ``DFMD(df=my_df, md=my_metadata)`` or ``DFMD(df="/path/to/df.csv",
            md=my_metadata)`` etc.

        # fixme: perhaps we should simply do that ourselves then?
        #   Unused objects should be garbage collected anyhow
        IMPORTANT CAVEAT: If you use df=<pd.DataFrame> or md=<dict like>,
        please be aware that this will not copy these objects, i.e. any
        changes that are done to these objects subsequently will affect both
        the original DataFrame/metadata and self.df or self.md.
        To avoid this, use pd.DataFrame.copy() or dict.copy() to create a
        deepcopy.

        Args:
            log: instance of logging.Logger or name of logger to be created
            *args: See above
            **kwargs: See above
        """
        # These are the three attributes of this class

        #: This will hold all the configuration that we will write out
        self.md = None
        #: Pandas dataframe to hold all of the results
        self.df = None  # type: pd.DataFrame
        #: instance of logging.Loggin
        self.log = None

        # First check if the user wants to initialize this class using
        # positional arguments. Handling of keyword arguments is done below.
        if len(args) == 0 and len(kwargs) == 0:
            # Initialize blank
            self.md = nested_dict()
            self.df = pd.DataFrame()
            self.log = None
        elif len(args) == 1:
            # Assume that we were given a DFMD object
            dfmd = args[0]
            self.md = dfmd.md
            self.df = dfmd.df
            self.log = dfmd.log

        # Handling this here, because it also sets the logger and we have to
        # be careful which logger specification takes priority
        if "dfmd" in kwargs:
            dfmd = kwargs["dfmd"]
            self.md = dfmd.md
            self.df = dfmd.df
            self.log = dfmd.log

        # Now we can set up the logger (because all other initializations
        # don't copy it)
        if isinstance(log, logging.Logger):
            self.log = log
        elif isinstance(log, str):
            self.log = get_logger(log)
        elif log is None:
            if not self.log:
                self.log = get_logger("DFMD")
        else:
            raise ValueError(
                "Unsupported type '{}' for 'log' argument.".format(
                    type(log)
                )
            )

        if len(args) == 2:
            # Assume we initialize from directory and name
            self.load(directory=args[0], name=args[1])
        elif len(args) >= 3:
            raise ValueError(
                "Got {} positional parameters and don't know what to do with"
                " them. Please check the signature of the "
                "intialization.".format(len(args))
            )

        # Now we turn to the kwargs
        # First we check if all keyword arguments are known
        known_kwargs = {
            "dfmd",
            "df",
            "md",
            "directory",
            "name",
        }
        unknown_kwargs = set(kwargs) - known_kwargs
        if unknown_kwargs:
            raise ValueError(
                "Unsupported keyword arguments: {}.".format(
                    ", ".join(list(unknown_kwargs))
                )
            )

        mixed_error = ValueError(
            "It looks like you are mixing initalization signatures. Please "
            "check the documentation about how to initialize the DFMD class."
        )

        # Now we go through all keyword arguments and try to execute them if
        # they make sense, else we throw mixed_error.

        if "df" in kwargs:
            if self.df is not None:
                raise mixed_error
            df = kwargs["df"]
            if isinstance(df, (PurePath, str)):
                self.load_df(df)
            elif isinstance(df, pd.DataFrame):
                self.df = kwargs["df"]
            else:
                raise ValueError(
                    "Unsupported type for df: '{}'.".format(type(df))
                )
        if "md" in kwargs:
            if self.md:
                raise mixed_error
            md = kwargs["md"]
            if isinstance(md, (PurePath, str)):
                self.load_md(md)
            elif isinstance(md, dict):
                # fixme: no, we need something more clever, because now it's
                #  just gonna be a normal dict instead of a nested_dict?
                self.md = md
            else:
                raise ValueError(
                    "Unsupported type for df: '{}'.".format(type(md))
                )

        if "directory" in kwargs:
            if "name" not in kwargs or self.md or self.df is not None:
                raise mixed_error
            self.load(kwargs["directory"], kwargs["name"])

    @property
    def was_scanned(self):
        return "scan" in self.md

    @property
    def was_clustered(self):
        return "cluster" in self.md

    @property
    def bin_cols(self):
        columns = list(self.df.columns)
        # todo: more general?
        return [c for c in columns if c.startswith("bin")]

    @property
    def par_cols(self):
        return self.md["scan"]["wpoints"]["coeffs"]

    @property
    def n(self):
        return len(self.df)

    @property
    def nbins(self):
        return len(self.bin_cols)

    @property
    def npars(self):
        return len(self.par_cols)

    def data_matrix(self):
        return self.df[self.bin_cols].values

    def load_md(self, md_path: Union[PurePath, str]) -> None:
        """ Load metadata from json file generated by DFMD.write_md."""
        md_path = Path(md_path)
        self.log.debug("Loading metadata from '{}'.".format(
            md_path.resolve())
        )
        with md_path.open() as metadata_file:
            md = json.load(metadata_file)
        # Make sure that we still have nested_dict as type for the metadata:
        self.md = nested_dict()
        self.md.update(md)
        self.log.debug("Done.")

    def write_md(self, md_path: Union[PurePath, str], overwrite="ask"):
        """

        Args:
            md_path:
            overwrite: How to proceed if output file already exists:
                'ask', 'overwrite', 'raise'

        Returns:

        """
        md_path = Path(md_path)

        self.log.info("Will write metadata to '{}'.".format(md_path))

        if not md_path .parent.is_dir():
            self.log.debug("Creating directory '{}'.".format(md_path .parent))
            md_path .parent.mkdir(parents=True)

        handle_overwrite([md_path], behavior=overwrite, log=self.log)

        with md_path.open("w") as metadata_file:
            json.dump(self.md, metadata_file, sort_keys=True, indent=4)

        self.log.debug("Done")

    def load_df(self, df_path: Union[PurePath, str]) -> None:
        """ Load dataframe from csv file creating by DFMD.write_md. """
        df_path = Path(df_path)
        self.log.debug("Loading scanner data from '{}'.".format(
            df_path.resolve()))
        with df_path.open() as data_file:
            self.df = pd.read_csv(data_file)
        self.df.set_index("index", inplace=True)
        self.log.debug("Loading done.")

    def write_df(self, df_path, overwrite="ask"):
        """

        Args:
            df_path:
            overwrite: How to proceed if output file already exists:
                'ask', 'overwrite', 'raise'

        Returns:

        """
        df_path = Path(df_path)

        self.log.info("Will write dataframe to '{}'.".format(df_path))

        if not df_path.parent.is_dir():
            self.log.debug("Creating directory '{}'.".format(df_path.parent))
            df_path.parent.mkdir(parents=True)

        handle_overwrite([df_path], behavior=overwrite, log=self.log)

        if self.df.empty:
            self.log.error(
                "Dataframe seems to be empty. Still writing out anyway."
            )

        with df_path.open("w") as data_file:
            self.df.to_csv(data_file)

        self.log.debug("Done")

    @staticmethod
    def get_df_path(directory: Union[PurePath, str], name: str) -> Path:
        """ Return path to metadata json file based on directory and project
        name.

        Args:
            directory: Path to input/output directory
            name: Name of project

        Returns:
            Path to metadata json file.
        """
        return Path(directory) / (name + "_data.csv")

    @staticmethod
    def get_md_path(directory: Union[PurePath, str], name: str) -> Path:
        """ Return path to dataframe csv file based on directory and project
        name.

        Args:
            directory: Path to input/output directory
            name: Name of project

        Returns:
            Path to dataframe csv file.
        """
        return Path(directory) / (name + "_metadata.json")

    def load(self, directory: Union[PurePath, str], name: str) -> None:
        """ Load from input files which have been generated from DFMD.write.

        Args:
            directory: Path to input/output directory
            name: Name of project

        Returns:
            None
        """
        self.load_df(self.get_df_path(directory, name))
        self.load_md(self.get_md_path(directory, name))

    def write(self, directory: Union[PurePath, str], name: str,
              overwrite="ask") -> None:
        """ Write to input files that can be later loaded with DFMD.write.

        Args:
            directory: Path to input/output directory
            name: Name of project
            overwrite: How to proceed if output file already exists:
                'ask', 'overwrite', 'raise'

        Returns:

        """
        df_path = self.get_df_path(directory, name)
        md_path = self.get_md_path(directory, name)
        handle_overwrite([df_path, md_path], behavior=overwrite, log=self.log)
        self.write_df(df_path, overwrite="overwrite")
        self.write_md(md_path, overwrite="overwrite")
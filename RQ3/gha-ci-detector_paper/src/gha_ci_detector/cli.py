import csv
import json
import os
import sys
from os import listdir
from os.path import isfile, join
from typing import Optional, Annotated, Set

import pandas as pd
import typer

from gha_ci_detector import __app_name__, __version__, util
from gha_ci_detector.Workflow import Workflow
from gha_ci_detector.Runner import Runner

app = typer.Typer()




# def main():
#     app(prog_name=__app_name__)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"{__app_name__} v{__version__}")
        raise typer.Exit()


@app.callback()
def main(version: Optional[bool] = typer.Option(
    None,
    "--version",
    "-v",
    help="Show application version and exit",
    callback=_version_callback, is_eager=True)) -> None:
    return


def analyze_and_report_workflow(workflow: Workflow, report: bool = True) -> Set[str]:
    runner = Runner(workflow)
    smells = runner.run_all()
    if report:
        util.print_smells(smells)
    if len(workflow.styling) > 0:
        print("The following styling errors were found: ")
        for s in workflow.styling:
            print(s)
    return smells


@app.command(name="all")
def analyze_all(workflow_folder: Annotated[Optional[str], typer.Argument()] = None) -> None:

    if workflow_folder is None:
        workflow_folder = "./.github/workflows"

    workflow_files = [join(workflow_folder, f) for f in listdir(workflow_folder)
                      if isfile(join(workflow_folder, f)) and (os.path.splitext(f)[1] == ".yml"
                                                               or os.path.splitext(f)[1] == ".yaml")]
    smell_count = {}
    all_smells = []
    for wf in workflow_files:
        workflow = Workflow.from_file(wf)
        all_smells += list(analyze_and_report_workflow(workflow))


@app.command(name="file")
def analyze_one(file_path: str = typer.Argument()) -> None:
    workflow = Workflow.from_file(file_path)
    analyze_and_report_workflow(workflow)


@app.command(name="path")
def analyze_path(directory_path: Annotated[Optional[str], typer.Argument()] = None) -> None:
    """
    Analyze all workflow files in the given directory path.
    """
    workflow_folder = directory_path if directory_path is not None else "./.github/workflows"

    workflow_files = [join(workflow_folder, f) for f in listdir(workflow_folder)
                      if isfile(join(workflow_folder, f))]
    smell_count = {}
    all_smells = []
    for wf in workflow_files:
        workflow = Workflow.from_file(wf)
        all_smells += list(analyze_and_report_workflow(workflow))


@app.command(name="csv")
def analyze_csv(
    csv_file_path: Annotated[Optional[str], typer.Argument()] = None,
    workflow_dir: Annotated[Optional[str], typer.Argument()] = None
) -> None:
    """
    Analyze workflow files in workflow_dir whose filename matches file_hash in the given CSV file.
    """
    if csv_file_path is None:
        print("CSV file path is required.", file=sys.stderr)
        return
    if workflow_dir is None:
        print("Workflow directory path is required.", file=sys.stderr)
        return

    # file_hash 목록 추출
    file_hashes = set()
    try:
        # pandas를 사용하여 CSV 파일을 더 안정적으로 읽음
        df = pd.read_csv(
            csv_file_path,
            engine='python',
            on_bad_lines='skip',
            encoding='utf-8',          # 인코딩을 UTF-8로 명시
            encoding_errors='ignore'   # 인코딩 오류 발생 시 무시
        fpath = os.path.join(workflow_dir, fname)
        if os.path.isfile(fpath) and fname in file_hashes:
            workflow = Workflow.from_file(fpath)
            if workflow and workflow.file_content: # 워크플로 객체가 유효하고 내용이 있는지 확인
                analyze_and_report_workflow(workflow)
            else:
                print(f"Skipping analysis for problematic file: {fname}")
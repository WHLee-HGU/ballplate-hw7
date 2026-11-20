"""실험 CSV에서 추종 오차를 계산합니다."""

import argparse
import csv
import math
import statistics


def read_samples(path):
    samples = []
    with open(path, encoding="utf-8-sig", newline="") as file:
        rows = csv.DictReader(file)
        fields = ("sim_t_s", "error_x_m", "error_y_m")
        if rows.fieldnames is None or not set(fields).issubset(rows.fieldnames):
            raise ValueError("CSV에 sim_t_s, error_x_m, error_y_m 열이 있어야 합니다.")
        for row in rows:
            try:
                sample = tuple(float(row[field]) for field in fields)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"CSV {rows.line_num}행의 숫자를 읽을 수 없습니다.") from exc
            if not all(math.isfinite(value) for value in sample):
                raise ValueError(f"CSV {rows.line_num}행에 유한하지 않은 숫자가 있습니다.")
            if samples and sample[0] <= samples[-1][0]:
                raise ValueError(f"CSV {rows.line_num}행의 시각이 이전 행보다 늦어야 합니다.")
            samples.append(sample)
    if not samples:
        raise ValueError("CSV에 기록된 샘플이 없습니다.")
    return samples


def main(args=None):
    parser = argparse.ArgumentParser(description="Ball on Plate 실험의 2차원 추종 오차를 요약합니다.")
    parser.add_argument("file", help="실험 CSV 경로")
    parser.add_argument("--start", type=float, default=0.0, help="첫 기록 이후 분석 시작 시각 [s]")
    parser.add_argument("--end", type=float, help="첫 기록 이후 분석 종료 시각 [s]")
    options = parser.parse_args(args)
    if not math.isfinite(options.start) or options.start < 0.0:
        parser.error("--start는 유한한 0 이상의 값이어야 합니다.")
    if options.end is not None and (
        not math.isfinite(options.end) or options.end <= options.start
    ):
        parser.error("--end는 유한하며 --start보다 커야 합니다.")

    try:
        samples = read_samples(options.file)
    except (OSError, csv.Error, ValueError) as exc:
        parser.error(str(exc))
    first_s = samples[0][0]
    coverage_s = samples[-1][0] - first_s
    end_s = coverage_s if options.end is None else options.end
    tolerance_s = 1e-9
    selected = [
        (stamp_s - first_s, error_x, error_y)
        for stamp_s, error_x, error_y in samples
        if options.start - tolerance_s <= stamp_s - first_s <= end_s + tolerance_s
    ]
    if not selected:
        parser.error(f"요청한 구간에 샘플이 없습니다. 기록 범위는 0.000–{coverage_s:.3f} s입니다.")

    distances_m = [math.hypot(error_x, error_y) for _, error_x, error_y in selected]
    rmse_mm = 1000.0 * math.sqrt(statistics.fmean(distance ** 2 for distance in distances_m))
    peak_mm = 1000.0 * max(distances_m)
    mean_x_mm = 1000.0 * statistics.fmean(error_x for _, error_x, _ in selected)
    mean_y_mm = 1000.0 * statistics.fmean(error_y for _, _, error_y in selected)
    print(f"기록 범위 0.000–{coverage_s:.3f} s / 총 {len(samples)}개")
    print(f"분석 범위 {selected[0][0]:.3f}–{selected[-1][0]:.3f} s / {len(selected)}개")
    if options.end is not None and coverage_s < options.end - tolerance_s:
        print(f"기록이 요청한 종료 시각 {options.end:.3f} s보다 일찍 끝났습니다.")
    print(f"2D RMSE {rmse_mm:.3f} mm / 최대 2D 오차 {peak_mm:.3f} mm")
    print(f"부호 있는 평균 오차 (목표−측정) X {mean_x_mm:+.3f} mm, Y {mean_y_mm:+.3f} mm")


if __name__ == "__main__":
    main()

#
# Author: Ben Hersh
# Class : Comp 3006 Winter 2021
import logging

import processors as cdp
import matplotlib.pyplot as plt
import numpy as np
import os

"""
Main data data processing pipeline.
1. Load the data
"""
COUNTIES_SOURCE_DATA = "../data/us-counties.csv"
CENSUS_REGION_DATA = "../data/census_cbsa.csv"
CENSUS_POPULATION_DATA = "../data/census_population_only_estimates_2019.csv"

def main():
    if os.path.exists("covid_prepped.csv"):
        covid_df = cdp.load_data("covid_prepped.csv")
    else:
        covid_df = step_1_data_prep()
    if os.path.exists("covid_by_state_year_month.csv"):
        by_state_df = cdp.load_data("covid_by_state_year_month.csv")
    else:
        by_state_df = step2_aggregate_by_state(covid_df)
    population_df = cdp.load_data("../data/census_population_only_estimates_2019.csv")
    # logging.info(population_df.info(verbose=True))
    # logging.info(population_df.head(10))
    population_df_agg = cdp.aggregate_covid_cases_by_group(None, ["STATE"], population_df, "POPESTIMATE2019")
    agg_pop_state_ids  = population_df_agg["STATE"].to_list()
    logging.info(population_df_agg.info(verbose=True))
    logging.info(population_df_agg.head(50))
    house_year_over_year_df = cdp.load_data("../../state_year_over_year_change.csv")
    quarters = [[1,2,3],[4,5,6],[7,8,9],[10,11,12]]
    for q_number, months in enumerate(quarters):
        house_year_over_year_by_quarter_df = house_year_over_year_df[house_year_over_year_df["Quarter"] == q_number+1]
        quarter_selection_df = by_state_df[(by_state_df["year"] == 2020) & (by_state_df["month"].isin(months))]
        covid_quarter_agg_df = cdp.aggregate_covid_cases_by_group(None, ["state_id"], quarter_selection_df, "new_cases_total")
        logging.info(covid_quarter_agg_df.head(50))
        sorted_covid_df = covid_quarter_agg_df.sort_values(by=["state_id"])
        sorted_housing_df = house_year_over_year_by_quarter_df.sort_values(by=["Place ID"])
        house_place_ids = sorted_housing_df["Place ID"]
        sorted_covid_df = sorted_covid_df[(sorted_covid_df["state_id"].isin(house_place_ids)) &
                                          (sorted_covid_df["state_id"].isin(agg_pop_state_ids))]
        sorted_covid_df["pop_estimate"] = population_df_agg["POPESTIMATE2019", "sum"] / 100000
        sorted_covid_df["new_cases_per_capita"] = sorted_covid_df["new_cases_total", "sum"] / sorted_covid_df["pop_estimate"]
        sorted_covid_df = sorted_covid_df[sorted_covid_df["new_cases_per_capita"] > 0]
        covid_state_ids = sorted_covid_df["state_id"].to_list()
        logging.info(sorted_housing_df.head(10))
        sorted_housing_for_covid_df = sorted_housing_df[sorted_housing_df["Place ID"].isin(covid_state_ids)]
        sorted_covid_df["log_new_cases"] = np.log10(sorted_covid_df["new_cases_per_capita"])
        logging.info(sorted_covid_df.info(verbose=True))
        logging.info(sorted_covid_df.head(50))
        plt.figure(1)
        plt.scatter(sorted_covid_df["log_new_cases"], sorted_housing_for_covid_df["YoY change"])
        plt.xlabel("Log10 Total New Cases per 100000")
        plt.ylabel("HPI Year of Year Change")
        plt.title(f"2020 Q{q_number+1} : Covid New Cases Per 100000 vs HPI Yearly Change")
        plt.savefig(f"q_{q_number+1}_covid_vs_hpi.png")
        plt.show()
        # plt.figure(1)
        # plt.scatter(sorted_covid_df["log_new_cases"], sorted_housing_df["% YoY change"])
        # plt.xlabel("Log10 Total New Cases")
        # plt.ylabel("HPI Year of Year Change")
        # plt.title(f"2020 Q{q_number+1} : Covid New Cases vs HPI % Yearly Change")
        # plt.savefig(f"q_{q_number+1}_covid_vs_hpi_percent.png")
        # plt.show()



#        logging.info("months : %s", months)
#        quarter_selection = by_state_df[(by_state_df["year"] == 2020) & (by_state_df["month"].isin(months))]
#        new_cases_agg = cdp.aggregate_covid_cases_by_group(None, ["state_id"], quarter_selection, "new_cases_total")
#        logging.info(new_cases_agg.head(100))
#        plt.figure(1)
#        plt.bar(new_cases_agg["state_id"], new_cases_agg["new_cases_total", "sum"])
#        plt.yscale("log")
#        plt.title(f"Q{q_number+1} 2020 : New Cases")
#        plt.xlabel("state id")
#        plt.ylabel("new cases")
#        plt.savefig(f"q{q_number+1}_new_cases.png")
#        plt.show()






def step2_aggregate_by_state(covid_df):
    states_series = covid_df["state_id"]
    states = states_series.unique()
    by_state_df = None
    for state_id in states:
        logging.info("getting aggregate for state id %d", state_id)
        state_df = covid_df[covid_df["state_id"] == state_id]
        state_df.sort_values(by=["date"])
        agg_result = cdp.aggregate_covid_cases_by_group(None, ["state_id", "year", "month"], state_df)
        agg_result["new_cases_total"] = agg_result["cases", "sum"] - agg_result["cases", "sum"].shift(1)
        if by_state_df is not None:
            by_state_df = by_state_df.append(agg_result)
        else:
            by_state_df = agg_result
#    logging.info(by_state_df.info(verbose=True))
#    logging.info(by_state_df.head(5))
#    logging.info(by_state_df.shape)
    by_state_df.to_csv("covid_by_state_year_month.csv", index=False)
    return by_state_df


def step_1_data_prep():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] [%(funcName)s] %(message)s")
    stdout_handler = logging.StreamHandler()
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.setFormatter(formatter)
    root_logger.addHandler(stdout_handler)
    # lets pick Central areas of Georgia
    census_cbsa_df = cdp.load_data(CENSUS_REGION_DATA)
    fips = cdp.find_fips_for_cbsa(12060, True, census_cbsa_df)
    covid_df = cdp.load_data(COUNTIES_SOURCE_DATA)
    cdp.split_covid_fips_into_cbsa_values(covid_df)
    covid_df.info(verbose=True)
    # logging.info(covid_df.head(5))
    covid_df.to_csv("covid_prepped.csv", index=False)
    return covid_df


if __name__ == "__main__":
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] [%(funcName)s] %(message)s")
    stdout_handler = logging.StreamHandler()
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.setFormatter(formatter)
    root_logger.addHandler(stdout_handler)
    main()

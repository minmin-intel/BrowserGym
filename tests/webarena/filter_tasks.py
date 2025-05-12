import json
import os
import pandas as pd

WORKDIR=os.getenv("WORKDIR", "")
DATAPATH=os.path.join(WORKDIR, "datasets/webarena")


def sample_one_per_site_per_intent_template(df, site):
    """
    Sample one task per intent template for a given site.
    """
    df_site = df[df["site"] == site]
    sampled_df = df_site.groupby("intent_template").sample(
        n=1,
        random_state=1
    ).to_csv(
        os.path.join(DATAPATH, f"test_{site}_sampled.csv"),
        index=False
    )
    return sampled_df


if __name__ == "__main__":

    datafile=os.path.join(DATAPATH, "test.raw.json")

    with open(datafile, "r") as f:
        data = json.load(f)

    site_list = []
    task_id_list = []
    intent_list = []
    ref_answer_list = []
    intent_template_list = []

    for d in data:
        sites = d["sites"]
        if len(sites) == 1:
            site_list.append(sites[0])
        else:
            site_entry = ""
            for site in sites:
                site_entry += f"{site}_"
            site_list.append(site_entry)
        task_id_list.append(d["task_id"])
        intent_list.append(d["intent"])
        ref_answer_list.append(d['eval']["reference_answers"])
        intent_template_list.append(d["intent_template_id"])

    df = pd.DataFrame({
        "site": site_list,
        "task_id": task_id_list,
        "intent": intent_list,
        "ref_answer": ref_answer_list,
        "intent_template": intent_template_list
    })
    # df.to_csv(os.path.join(DATAPATH, "test.csv"), index=False)

    print(df.groupby("site").size().reset_index(name="counts"))

    unqiue_sites = df["site"].unique()
    for site in unqiue_sites:
        print(f"Sampling one task per intent template for {site}")
        sampled_df = sample_one_per_site_per_intent_template(df, site)






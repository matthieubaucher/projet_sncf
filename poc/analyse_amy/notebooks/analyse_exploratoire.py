import math
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns



def separer_variables(df, variables_temporelles=None):
    if variables_temporelles is None:
        variables_temporelles = []

    variables_temporelles = [col for col in variables_temporelles if col in df.columns]

    variables_numeriques = df.select_dtypes(include="number").columns.difference(variables_temporelles).tolist()

    variables_categorielles = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()

    # Ajouter les variables temporelles aux catégories dédiées
    variables_temporelles_detectees = [
    col for col in df.columns
    if pd.api.types.is_datetime64_any_dtype(df[col])
]
    variables_temporelles = list(dict.fromkeys(variables_temporelles + variables_temporelles_detectees
    ))

    return {
        "numeriques": variables_numeriques,
        "categorielles": variables_categorielles,
        "temporelles": variables_temporelles
    }
    
    
def analyser_variables_numeriques(df, variables, nom_dataset="Dataset"):
    if not variables:
        print("Aucune variable numérique à analyser.")
        return

    print(f"\nStatistiques descriptives — {nom_dataset}")
    df[variables].describe().T

    for debut in range(0, len(variables), 4):
        groupe = variables[debut:debut + 4]

        fig, axes = plt.subplots(
            len(groupe), 2,
            figsize=(14, 4 * len(groupe)),
            squeeze=False
        )

        for i, col in enumerate(groupe):
            valeurs = df[col].dropna()

            sns.histplot(
                valeurs,
                kde=valeurs.nunique() > 10,
                ax=axes[i, 0]
            )
            axes[i, 0].set_title(f"Distribution — {col}")
            axes[i, 0].set_xlabel(col)
            axes[i, 0].set_ylabel("Effectif")

            sns.boxplot(x=valeurs, ax=axes[i, 1])
            axes[i, 1].set_title(f"Boxplot — {col}")
            axes[i, 1].set_xlabel(col)

        plt.tight_layout()
        plt.show()
    
    
def analyser_variables_categorielles(df, variables, nom_dataset="Dataset", top_n=20):
    if not variables:
        print("Aucune variable catégorielle à analyser.")
        return

    for col in variables:
        print(f"\n{col} — {nom_dataset}")

        effectifs = df[col].value_counts(
            dropna=False
        ).head(top_n)

        proportions = (
            df[col].value_counts(normalize=True, dropna=False)
            .head(top_n) * 100
        )

        tableau = pd.DataFrame({
            "Effectif": effectifs,
            "Pourcentage (%)": proportions.round(2)
        })

        print(tableau)

        ax = effectifs.sort_values().plot(
            kind="barh",
            figsize=(10, max(3, len(effectifs) * 0.35))
        )
        ax.set_title(f"Modalités les plus fréquentes — {col}")
        ax.set_xlabel("Effectif")
        ax.set_ylabel(col)

        plt.tight_layout()
        plt.show()
        
        
def analyse_exploratoire(
    df,
    nom_dataset="Dataset",
    variables_temporelles=None,
    top_n=20
):
    print("=" * 70)
    print(f"ANALYSE EXPLORATOIRE : {nom_dataset}")
    print("=" * 70)

    print("\n1. Dimensions")
    print(f"Nombre de lignes : {df.shape[0]}")
    print(f"Nombre de colonnes : {df.shape[1]}")

    print("\n2. Valeurs manquantes")
    manquants = df.isna().sum()
    print(
        manquants[manquants > 0]
        .sort_values(ascending=False)
        .to_frame("Valeurs manquantes")
    )

    types = separer_variables(df, variables_temporelles)

    print("\n3. Variables numériques")
    print(types["numeriques"])

    print("\n4. Variables catégorielles")
    print(types["categorielles"])

    print("\n5. Variables temporelles")
    print(types["temporelles"])

    analyser_variables_numeriques(
        df, types["numeriques"], nom_dataset
    )

    analyser_variables_categorielles(
        df, types["categorielles"], nom_dataset, top_n
    )

    return types
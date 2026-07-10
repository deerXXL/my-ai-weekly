export async function fetchReport(file=null){

    let url="/api/report";


    if(file){

        url += `?file=${file}`;

    }


    const response =
        await fetch(url);


    if(!response.ok){

        throw new Error(
            "report api error"
        );

    }


    return await response.json();

}


export async function fetchArchive(){

    const response = await fetch("/api/archive");

    if(!response.ok){
        throw new Error("archive api error");
    }

    return await response.json();

}
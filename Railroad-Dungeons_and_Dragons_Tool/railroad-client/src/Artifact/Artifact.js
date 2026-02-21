import React, { useEffect, useState } from "react";
import FactList from "./FactList";
import { useSelector, useDispatch } from "react-redux";
import { Button, Container } from "@mui/joy";
import { Add, DeleteOutline } from "@mui/icons-material";
import { focus, refresh } from "./artifactSlice";
import EditableText from "../components/EditableText";
import styled from "styled-components";

const Wrapper = styled(Container)`
  padding: 10px;
  height: calc(100vh - 40px);
  overflow: scroll;
`;

export default function Artifact() {
  const artifactId = useSelector((state) => state.artifact.id);
  const refreshReq = useSelector((state) => state.artifact.refresh);
  const [artifact, setArtifact] = useState(null);
  const [facts, setFacts] = useState([]);
  const dispatch = useDispatch();

  useEffect(() => {
    if (!refreshReq) return;
    console.log("here");
    fetch(`/api/artifact/${artifactId}`)
      .then((res) => res.json())
      .then((data) => setArtifact(data[0]));
    fetch(`/api/fact/list/${artifactId}`)
      .then((res) => res.json())
      .then((data) => setFacts(data));
    dispatch(refresh(false));
  }, [refreshReq]);

  useEffect(() => {
    if (artifactId == null) {
      setArtifact(null);
      setFacts([]);
    } else {
      dispatch(refresh(true));
    }
  }, [artifactId]);

  const deleteArtifact = () => {
    fetch(`/api/artifact/${artifactId}`, { method: "DELETE" }).then(() =>
      dispatch(focus(null))
    );
  };

  const addFact = () => {
    fetch(`/api/fact/${artifactId}`, { method: "PUT" })
      .then((res) => res.json())
      .then((data) => setFacts([...facts, data]));
  };

  if (!artifact || (facts.length > 0 && artifact.id !== facts[0].artifact_id))
    return null;

  return (
    <Wrapper>
      <Button onClick={deleteArtifact}>
        <DeleteOutline />
      </Button>
      <EditableText
        get={() =>
          fetch(`/api/artifact/${artifactId}`)
            .then((res) => res.json())
            .then((data) => data[0].title)
        }
        set={(value) =>
          fetch(`/api/artifact/${artifactId}?title=${value}`, {
            method: "POST",
          })
        }
      />
      <FactList list={facts} />
      <Button onClick={addFact}>
        <Add />
      </Button>
    </Wrapper>
  );
}

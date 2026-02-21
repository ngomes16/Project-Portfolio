import React, { useEffect, useState } from "react";
import ArtifactList from "./ArtifactList";
import { Button, Checkbox, TextField } from "@mui/joy";
import { useSelector, useDispatch } from "react-redux";
import { focus } from "../Artifact/artifactSlice";
import { Add } from "@mui/icons-material";
import { Stack } from "@mui/joy";
import styled from "styled-components";

const Wrapper = styled(Stack)`
  height: 400px;
  width: 300px;
`;

export default function Sidebar() {
  const [searchInput, setSearchInput] = useState("");
  const [list, setList] = useState([]);
  const [titleOnly, setTitleOnly] = useState(true);
  const dispatch = useDispatch();
  const artifactId = useSelector((state) => state.artifact.id);

  const search = () => {
    if (searchInput === "") {
      return;
    }
    fetch(`/api/search?keyword=${searchInput}`)
      .then((res) => res.json())
      .then((data) => setList(data));
  };

  useEffect(() => {
    if (artifactId == null) {
      return search();
    }
  }, [artifactId]);

  const handleSearchInput = (e) => {
    e.preventDefault();
    setSearchInput(e.target.value);
    search();
  };
  const handleTitleOnlyChange = (e) => {
    setTitleOnly(e.target.checked);
  };
  const createNewArtifact = () => {
    fetch(`/api/artifact`, { method: "PUT" })
      .then((res) => res.json())
      .then((data) => dispatch(focus(data.id)));
  };

  return (
    <Wrapper>
      <Checkbox
        label="Title Only"
        onChange={handleTitleOnlyChange}
        checked={titleOnly}
      />
      <TextField
        placeholder="Search"
        variant="outlined"
        onChange={handleSearchInput}
      />
      <Button onClick={createNewArtifact}>
        <Add />
      </Button>
      <ArtifactList
        list={
          titleOnly
            ? list.filter((art) =>
                art.title.match(new RegExp(searchInput, "i"))
              )
            : list
        }
      />
    </Wrapper>
  );
}

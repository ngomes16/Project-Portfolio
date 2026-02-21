import React, { useEffect, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import { Button, Stack } from "@mui/joy";
import { Check, DeleteOutline, EditOutlined } from "@mui/icons-material";
import MDEditor from "@uiw/react-md-editor";
import { Textarea } from "@mui/joy";
import styled from "styled-components";

const Editor = styled(MDEditor)`
  width: 100%;
`;

const Viewer = styled(MDEditor.Markdown)`
  width: 100%;
`;

const Controls = styled(Stack)`
  & > * {
    width: 10px;
  }
`;

const Wrapper = styled(Stack).attrs((props) => ({
  direction: "row",
  spacing: 2,
  justifyContent: "space-between",
}))``;

export default function EditableText({ get, set, del }) {
  const [editMode, setEditMode] = useState(false);
  const [content, setContent] = useState("");

  useEffect(() => {
    if (!editMode) get().then((data) => setContent(data));
  }, [editMode]);

  if (!editMode)
    return (
      <Wrapper>
        <Viewer source={content} />
        <Controls>
          <Button onClick={() => setEditMode(true)}>
            <EditOutlined />
          </Button>
          {del ? (
            <Button onClick={() => del()}>
              <DeleteOutline />
            </Button>
          ) : null}
        </Controls>
      </Wrapper>
    );

  return (
    <Wrapper>
      <Editor value={content} onChange={setContent} />
      <Controls>
        <Check
          onClick={async () => {
            await set(content);
            setEditMode(false);
          }}
        />
      </Controls>
    </Wrapper>
  );
}
